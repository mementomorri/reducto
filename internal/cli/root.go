package cli

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/alexkarsten/reducto/internal/config"
	"github.com/alexkarsten/reducto/internal/git"
	"github.com/alexkarsten/reducto/internal/mcp"
	"github.com/alexkarsten/reducto/internal/reporter"
	"github.com/alexkarsten/reducto/internal/sidecar"
	"github.com/alexkarsten/reducto/pkg/models"
	"github.com/spf13/cobra"
)

var (
	cfgFile      string
	verbose      bool
	model        string
	preferLocal  bool
	preferRemote bool
	cfg          *models.Config
	mcpManager   *sidecar.MCPManager
)

var rootCmd = &cobra.Command{
	Use:   "reducto",
	Short: "Semantic Code Compression Engine",
	Long: `reducto is an autonomous code compression utility that optimizes 
and compresses codebases while maintaining 100% functional parity.

It identifies repeating patterns, suggests idiomatic improvements, 
and applies design patterns to reduce cognitive load.`,
	PersistentPreRunE: func(cmd *cobra.Command, args []string) error {
		var err error
		cfg, err = config.Load(cfgFile)
		if err != nil {
			return fmt.Errorf("failed to load config: %w", err)
		}

		if verbose {
			cfg.Verbose = true
		}

		if model != "" {
			cfg.Model = model
		}

		if preferRemote {
			cfg.PreferLocal = false
		} else if cmd.Flags().Changed("prefer-local") {
			cfg.PreferLocal = preferLocal
		}

		return nil
	},
}

func init() {
	rootCmd.PersistentFlags().StringVarP(&cfgFile, "config", "c", "", "config file (default is $HOME/.reducto.yaml)")
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "verbose output")
	rootCmd.PersistentFlags().StringVar(&model, "model", "", "LLM model override (e.g., gpt-4o, ollama/qwen2.5-coder:1.5b)")
	rootCmd.PersistentFlags().BoolVar(&preferLocal, "prefer-local", true, "prefer local Ollama models")
	rootCmd.PersistentFlags().BoolVar(&preferRemote, "prefer-remote", false, "prefer remote cloud models")
}

// Helper functions for CLI commands

func handleDryRun(dryRun bool, path string) error {
	if dryRun {
		fmt.Println("=== DRY RUN MODE - No changes will be applied ===")
		return nil
	}
	return checkGitState(path)
}

func runWithSpinner(operation string, inProgress string, complete string, fn func() error) error {
	fmt.Printf("%s...\n", operation)
	done := make(chan struct{})
	finished := showSpinner(done, inProgress, complete)
	err := fn()
	close(done)
	<-finished
	return err
}

func printChangeCount(count int, itemType string) {
	fmt.Printf("\n")
	if count == 0 {
		fmt.Printf("No %s found.\n", itemType)
		return
	}
	fmt.Printf("Found %d %s opportunity(ies)\n", count, itemType)
}

func promptForApproval() error {
	if cfg.PreApprove {
		return nil
	}
	fmt.Printf("\nApply these changes? [y/N]: ")
	var response string
	fmt.Scanln(&response)
	if response != "y" && response != "Y" {
		return fmt.Errorf("aborted by user")
	}
	return nil
}

func applyChangesAndReport(plan *models.RefactorPlan, command string, path string, generateReport bool) error {
	changeCount := len(plan.Changes)
	printChangeCount(changeCount, strings.TrimSuffix(command, "e"))
	if changeCount == 0 {
		return nil
	}

	if cfg.Verbose {
		fmt.Printf("\n%s\n", plan.Description)
	} else {
		fmt.Printf("\nRun with -v for details.\n")
	}

	if generateReport {
		fmt.Printf("\nSession ID: %s\n", plan.SessionID)
	}

	if err := promptForApproval(); err != nil {
		return err
	}

	fmt.Printf("\nApplying %d change(s)...\n", changeCount)
	applyResult, err := mcpManager.ApplyPlan(plan, true)
	if err != nil {
		fmt.Printf("Warning: Some changes may have been rolled back: %v\n", err)
	}
	if applyResult != nil && applyResult.Success {
		fmt.Printf("✓ All changes applied successfully.\n")
	} else if applyResult != nil {
		fmt.Printf("✗ Some changes failed: %s\n", applyResult.Error)
	}
	if generateReport && applyResult != nil {
		rep := reporter.New(cfg)
		if err := rep.Generate(applyResult); err != nil {
			fmt.Printf("Warning: Failed to generate report: %v\n", err)
		} else {
			fmt.Printf("Report generated for session %s.\n", plan.SessionID)
		}
	}
	return nil
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func checkGitState(path string) error {
	gitMgr := git.NewManager(path)
	clean, err := gitMgr.IsClean()
	if err != nil {
		return fmt.Errorf("failed to check git state: %w", err)
	}

	if !clean {
		fmt.Println("Warning: You have uncommitted changes.")
		fmt.Println("It is recommended to commit or stash your changes before refactoring.")

		if cfg.PreApprove {
			fmt.Println("Proceeding anyway (--yes flag set)...")
			return nil
		}

		fmt.Print("Continue anyway? [y/N]: ")
		var response string
		fmt.Scanln(&response)
		if response != "y" && response != "Y" {
			return fmt.Errorf("aborted by user")
		}
	}

	return nil
}

func showSpinner(done <-chan struct{}, inProgress string, complete string) <-chan struct{} {
	finished := make(chan struct{})
	go func() {
		spinner := []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}
		i := 0
		for {
			select {
			case <-done:
				fmt.Printf("\r✓ %s    \n", complete)
				close(finished)
				return
			default:
				fmt.Printf("\r%s %s...", spinner[i%len(spinner)], inProgress)
				i++
				time.Sleep(80 * time.Millisecond)
			}
		}
	}()
	return finished
}

func runAnalyzeCore(path string) (*sidecar.AnalyzeResult, error) {
	fmt.Printf("Analyzing repository...\n")

	done := make(chan struct{})
	finished := showSpinner(done, "Analyzing", "Analysis complete")

	mcpManager = sidecar.NewMCPManager(path, cfg)
	result, err := mcpManager.Analyze(path)
	close(done)
	<-finished

	if err != nil {
		return nil, fmt.Errorf("analysis failed: %w", err)
	}

	return result, nil
}

func printAnalyzeResult(result *sidecar.AnalyzeResult) {
	fmt.Printf("\n")
	fmt.Printf("Files: %d  Symbols: %d  Hotspots: %d\n", result.TotalFiles, result.TotalSymbols, len(result.Hotspots))

	if len(result.Hotspots) > 0 && cfg.Verbose {
		fmt.Printf("\n--- Complexity Hotspots ---\n")
		for _, hs := range result.Hotspots {
			fmt.Printf("  %s:%d - %s (CC: %d)\n", hs.File, hs.Line, hs.Symbol, hs.CyclomaticComplexity)
		}
	} else if len(result.Hotspots) > 0 {
		fmt.Printf("\nRun with -v for hotspot details.\n")
	}
}

func runAnalyze(path string) error {
	result, err := runAnalyzeCore(path)
	if err != nil {
		return err
	}

	printAnalyzeResult(result)
	return nil
}

func runAnalyzeWithReport(path string) error {
	result, err := runAnalyzeCore(path)
	if err != nil {
		return err
	}

	printAnalyzeResult(result)

	baseline := &reporter.BaselineResult{
		TotalFiles:   result.TotalFiles,
		TotalSymbols: result.TotalSymbols,
		Hotspots:     make([]reporter.ComplexityHotspot, len(result.Hotspots)),
	}
	for i, hs := range result.Hotspots {
		baseline.Hotspots[i] = reporter.ComplexityHotspot{
			File:                 hs.File,
			Line:                 hs.Line,
			Symbol:               hs.Symbol,
			CyclomaticComplexity: hs.CyclomaticComplexity,
			CognitiveComplexity:  hs.CognitiveComplexity,
		}
	}

	rep := reporter.New(cfg)
	if err := rep.GenerateBaseline(baseline); err != nil {
		return fmt.Errorf("failed to generate baseline report: %w", err)
	}

	fmt.Printf("Baseline report generated.\n")
	return nil
}

func runDeduplicate(path string, commitChanges bool, generateReport bool, dryRun bool) error {
	if err := handleDryRun(dryRun, path); err != nil {
		return err
	}

	var plan *models.RefactorPlan
	err := runWithSpinner("Finding duplicate code", "Finding duplicates", "Deduplication analysis complete", func() error {
		mcpManager = sidecar.NewMCPManager(path, cfg)
		var err error
		plan, err = mcpManager.Deduplicate(path)
		return err
	})
	if err != nil {
		return fmt.Errorf("deduplication planning failed: %w", err)
	}

	if dryRun {
		rep := reporter.New(cfg)
		return rep.GenerateDryRun(plan, "deduplicate", path)
	}

	return applyChangesAndReport(plan, "deduplicate", path, generateReport)
}

func runIdiomatize(path string, dryRun bool) error {
	if err := handleDryRun(dryRun, path); err != nil {
		return err
	}

	var plan *models.RefactorPlan
	err := runWithSpinner("Finding idiomatization opportunities", "Analyzing code patterns", "Idiomatization analysis complete", func() error {
		mcpManager = sidecar.NewMCPManager(path, cfg)
		var err error
		plan, err = mcpManager.Idiomatize(path)
		return err
	})
	if err != nil {
		return fmt.Errorf("idiomatization planning failed: %w", err)
	}

	if dryRun {
		rep := reporter.New(cfg)
		return rep.GenerateDryRun(plan, "idiomatize", path)
	}

	return applyChangesAndReport(plan, "idiomatize", path, false)
}

func runPattern(pattern, path string, dryRun bool) error {
	if err := handleDryRun(dryRun, path); err != nil {
		return err
	}

	var plan *models.RefactorPlan
	operation := "Finding pattern opportunities"
	if pattern != "" {
		operation = fmt.Sprintf("Applying pattern: %s", pattern)
	}

	err := runWithSpinner(operation, "Analyzing patterns", "Pattern analysis complete", func() error {
		mcpManager = sidecar.NewMCPManager(path, cfg)
		var err error
		plan, err = mcpManager.ApplyPattern(pattern, path)
		return err
	})
	if err != nil {
		return fmt.Errorf("pattern injection failed: %w", err)
	}

	if dryRun {
		rep := reporter.New(cfg)
		return rep.GenerateDryRun(plan, "pattern", path)
	}

	return applyChangesAndReport(plan, "pattern", path, false)
}

func runReport(sessionID string) error {
	rep := reporter.New(cfg)
	return rep.Load(sessionID)
}

func runMCP(path string) error {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigChan
		cancel()
	}()

	server := mcp.NewServer(path)
	defer server.Shutdown()

	return server.Start(ctx, os.Stdin, os.Stdout)
}

func runCheck(path string) error {
	fmt.Printf("Checking code quality...\n")

	done := make(chan struct{})
	finished := showSpinner(done, "Analyzing", "Analysis complete")

	mcpManager = sidecar.NewMCPManager(path, cfg)
	result, err := mcpManager.Check(path)
	close(done)
	<-finished

	if err != nil {
		return fmt.Errorf("quality check failed: %w", err)
	}

	totalIssues := int(result["total_issues"].(float64))
	critical := int(result["critical"].(float64))
	warnings := int(result["warning"].(float64))
	info := int(result["info"].(float64))

	fmt.Printf("\n")
	if totalIssues == 0 {
		fmt.Printf("✓ No issues found!\n")
		return nil
	}

	fmt.Printf("Found %d issue(s)\n", totalIssues)
	fmt.Printf("  ✗ Critical: %d\n", critical)
	fmt.Printf("  ⚠ Warning:  %d\n", warnings)
	fmt.Printf("  ℹ Info:     %d\n", info)

	if !cfg.Verbose {
		fmt.Printf("\nRun with -v for detailed output.\n")
		return nil
	}

	if issues, ok := result["issues"].([]interface{}); ok && len(issues) > 0 {
		fmt.Printf("\n--- Details ---\n")
		for _, issue := range issues {
			if i, ok := issue.(map[string]interface{}); ok {
				severity := i["severity"].(string)
				file := i["file"].(string)
				line := i["line"].(float64)
				issueType := i["issue_type"].(string)
				message := i["message"].(string)
				symbol, _ := i["symbol"].(string)

				severityIcon := "ℹ"
				if severity == "critical" {
					severityIcon = "✗"
				} else if severity == "warning" {
					severityIcon = "⚠"
				}

				fmt.Printf("  %s %s:%d - [%s] %s", severityIcon, file, int(line), issueType, message)
				if symbol != "" {
					fmt.Printf(" (%s)", symbol)
				}
				fmt.Println()

				if suggestion, ok := i["suggestion"].(string); ok && suggestion != "" {
					fmt.Printf("      → %s\n", suggestion)
				}
			}
		}
	}

	return nil
}

func runSessionsList(cmd *cobra.Command, args []string) error {
	fmt.Printf("Listing stored sessions...\n")

	mcpManager = sidecar.NewMCPManager(".", cfg)
	sessions, err := mcpManager.ListSessions()
	if err != nil {
		return fmt.Errorf("failed to list sessions: %w", err)
	}

	if len(sessions) == 0 {
		fmt.Printf("No stored sessions found.\n")
		fmt.Printf("Sessions are stored in: .reducto/sessions/\n")
		return nil
	}

	fmt.Printf("Found %d session(s):\n\n", len(sessions))
	fmt.Printf("%-40s %-15s %-10s %-10s %s\n", "Session ID", "Command", "Files", "Changes", "Created")
	fmt.Printf("%s\n", strings.Repeat("-", 100))

	for _, s := range sessions {
		sessionID, _ := s["session_id"].(string)
		commandType, _ := s["command_type"].(string)
		fileCount, _ := s["file_count"].(float64)
		changeCount, _ := s["change_count"].(float64)
		createdAt, _ := s["created_at"].(string)

		fmt.Printf("%-40s %-15s %-10.0f %-10.0f %s\n",
			sessionID[:min(40, len(sessionID))],
			commandType,
			fileCount,
			changeCount,
			createdAt[:min(19, len(createdAt))])
	}

	return nil
}

func runSessionsShow(cmd *cobra.Command, args []string) error {
	sessionID := args[0]
	fmt.Printf("Showing session: %s\n\n", sessionID)

	mcpManager = sidecar.NewMCPManager(".", cfg)
	plan, err := mcpManager.GetSession(sessionID)
	if err != nil {
		return fmt.Errorf("failed to get session: %w", err)
	}

	if plan == nil {
		return fmt.Errorf("session not found: %s", sessionID)
	}

	fmt.Printf("Description: %s\n", plan.Description)
	fmt.Printf("Pattern: %s\n", plan.Pattern)
	fmt.Printf("Changes: %d\n\n", len(plan.Changes))

	for i, change := range plan.Changes {
		fmt.Printf("%d. %s\n", i+1, change.Path)
		fmt.Printf("   %s\n\n", change.Description)
	}

	return nil
}

func runSessionsCleanup(cmd *cobra.Command, args []string) error {
	fmt.Println("Session cleanup is handled by the Python sidecar.")
	fmt.Println("To clean up sessions, use the Python sidecar API or manually delete files in: .reducto/sessions/")
	return nil
}

func runApply(sessionID string, dryRun bool) error {
	if dryRun {
		fmt.Println("=== DRY RUN MODE - No changes will be applied ===")
	} else {
		if err := checkGitState("."); err != nil {
			return err
		}
	}

	fmt.Println("Apply session is handled by the Python sidecar.")
	fmt.Println("To apply a saved session, use the Python sidecar API.")
	fmt.Printf("Session ID provided: %s\n", sessionID)
	return nil
}

var analyzeCmd = &cobra.Command{
	Use:   "analyze [path]",
	Short: "Analyze repository for compression opportunities",
	Long: `Scans the repository to identify:
- Code duplication patterns
- Complexity hotspots
- Non-idiomatic code sections
- Opportunities for design pattern injection`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		path := "."
		if len(args) > 0 {
			path = args[0]
		}

		generateReport, _ := cmd.Flags().GetBool("report")

		if generateReport {
			return runAnalyzeWithReport(path)
		}
		return runAnalyze(path)
	},
}

var deduplicateCmd = &cobra.Command{
	Use:   "deduplicate [path]",
	Short: "Find and eliminate code duplication",
	Long: `Identifies semantically similar code blocks across the repository
and suggests or applies refactoring to eliminate duplication.`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		path := "."
		if len(args) > 0 {
			path = args[0]
		}

		preApprove, _ := cmd.Flags().GetBool("yes")
		cfg.PreApprove = preApprove

		commitChanges, _ := cmd.Flags().GetBool("commit")
		generateReport, _ := cmd.Flags().GetBool("report")
		dryRun, _ := cmd.Flags().GetBool("dry-run")

		return runDeduplicate(path, commitChanges, generateReport, dryRun)
	},
}

var idiomatizeCmd = &cobra.Command{
	Use:   "idiomatize [path]",
	Short: "Transform code to idiomatic patterns",
	Long: `Identifies non-idiomatic code patterns and suggests
or applies transformations to make code more idiomatic.`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		path := "."
		if len(args) > 0 {
			path = args[0]
		}

		preApprove, _ := cmd.Flags().GetBool("yes")
		cfg.PreApprove = preApprove
		dryRun, _ := cmd.Flags().GetBool("dry-run")

		return runIdiomatize(path, dryRun)
	},
}

var patternCmd = &cobra.Command{
	Use:   "pattern [pattern] [path]",
	Short: "Apply a design pattern to simplify code",
	Long: `Identifies opportunities for design pattern injection
(such as Factory, Strategy, Observer) and applies refactoring.`,
	Args: cobra.MaximumNArgs(2),
	RunE: func(cmd *cobra.Command, args []string) error {
		pattern := ""
		path := "."

		if len(args) > 0 {
			pattern = args[0]
		}
		if len(args) > 1 {
			path = args[1]
		}

		preApprove, _ := cmd.Flags().GetBool("yes")
		cfg.PreApprove = preApprove
		dryRun, _ := cmd.Flags().GetBool("dry-run")

		return runPattern(pattern, path, dryRun)
	},
}

var reportCmd = &cobra.Command{
	Use:   "report",
	Short: "Generate a compression report",
	Long:  `Generates a detailed report of the last compression session.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		sessionID, _ := cmd.Flags().GetString("session")
		return runReport(sessionID)
	},
}

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print the version number",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("reducto v0.1.0")
	},
}

var mcpCmd = &cobra.Command{
	Use:   "mcp [path]",
	Short: "Start MCP server for tool access",
	Long: `Starts the MCP (Model Context Protocol) server that provides
tools for file operations, symbol extraction, diff application, etc.

The server reads JSON-RPC requests from stdin and writes responses to stdout.
This is primarily used by the Python AI sidecar for communication.`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		path := "."
		if len(args) > 0 {
			path = args[0]
		}

		return runMCP(path)
	},
}

var checkCmd = &cobra.Command{
	Use:   "check [path]",
	Short: "Check code quality and detect problematic patterns",
	Long: `Analyzes code for quality issues including:
- Unpronounceable/cryptic variable names
- Single-letter variables in non-loop contexts
- Long functions (over 50 lines)
- High complexity code
- Naming convention violations`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		path := "."
		if len(args) > 0 {
			path = args[0]
		}

		return runCheck(path)
	},
}

var sessionsCmd = &cobra.Command{
	Use:   "sessions",
	Short: "Manage refactoring sessions",
	Long:  `List, view, and manage stored refactoring sessions.`,
}

var sessionsListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all stored sessions",
	RunE:  runSessionsList,
}

var sessionsShowCmd = &cobra.Command{
	Use:   "show <session-id>",
	Short: "Show details for a session",
	Args:  cobra.ExactArgs(1),
	RunE:  runSessionsShow,
}

var sessionsCleanupCmd = &cobra.Command{
	Use:   "cleanup",
	Short: "Remove old sessions (older than 7 days)",
	RunE:  runSessionsCleanup,
}

var applyCmd = &cobra.Command{
	Use:   "apply <session-id>",
	Short: "Apply a stored refactoring plan",
	Long:  `Load and apply changes from a previously generated refactoring session.`,
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		sessionID := args[0]
		dryRun, _ := cmd.Flags().GetBool("dry-run")
		return runApply(sessionID, dryRun)
	},
}

func initCommands() {
	analyzeCmd.Flags().Bool("report", false, "generate baseline report after analysis")
	deduplicateCmd.Flags().BoolP("yes", "y", false, "skip approval and apply changes automatically")
	deduplicateCmd.Flags().Bool("commit", false, "commit changes to git after successful refactoring")
	deduplicateCmd.Flags().Bool("report", false, "generate report after deduplication")
	deduplicateCmd.Flags().Bool("dry-run", false, "show proposed changes without applying")
	idiomatizeCmd.Flags().BoolP("yes", "y", false, "skip approval and apply changes automatically")
	idiomatizeCmd.Flags().Bool("report", false, "generate report after idiomatization")
	idiomatizeCmd.Flags().Bool("dry-run", false, "show proposed changes without applying")
	patternCmd.Flags().BoolP("yes", "y", false, "skip approval and apply changes automatically")
	patternCmd.Flags().Bool("report", false, "generate report after pattern injection")
	patternCmd.Flags().Bool("dry-run", false, "show proposed changes without applying")
	reportCmd.Flags().StringP("session", "s", "", "session ID to report (default: last session)")
	applyCmd.Flags().BoolP("yes", "y", false, "skip approval and apply changes automatically")
	applyCmd.Flags().Bool("dry-run", false, "show proposed changes without applying")

	rootCmd.AddCommand(analyzeCmd)
	rootCmd.AddCommand(deduplicateCmd)
	rootCmd.AddCommand(idiomatizeCmd)
	rootCmd.AddCommand(patternCmd)
	rootCmd.AddCommand(reportCmd)
	rootCmd.AddCommand(versionCmd)
	rootCmd.AddCommand(mcpCmd)
	rootCmd.AddCommand(checkCmd)
	rootCmd.AddCommand(applyCmd)

	sessionsCmd.AddCommand(sessionsListCmd)
	sessionsCmd.AddCommand(sessionsShowCmd)
	sessionsCmd.AddCommand(sessionsCleanupCmd)
	rootCmd.AddCommand(sessionsCmd)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func init() {
	initCommands()
}
