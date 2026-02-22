package cli

import (
	"context"
	"fmt"
	"os"
	"os/signal"
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

func runAnalyze(path string) error {
	fmt.Printf("Analyzing repository...\n")

	done := make(chan struct{})
	finished := showSpinner(done, "Analyzing", "Analysis complete")

	mcpManager = sidecar.NewMCPManager(path, cfg)
	result, err := mcpManager.Analyze(path)
	close(done)
	<-finished

	if err != nil {
		return fmt.Errorf("analysis failed: %w", err)
	}

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

	return nil
}

func runAnalyzeWithReport(path string) error {
	fmt.Printf("Analyzing repository...\n")

	done := make(chan struct{})
	finished := showSpinner(done, "Analyzing", "Analysis complete")

	mcpManager = sidecar.NewMCPManager(path, cfg)
	result, err := mcpManager.Analyze(path)
	close(done)
	<-finished

	if err != nil {
		return fmt.Errorf("analysis failed: %w", err)
	}

	fmt.Printf("\n")
	fmt.Printf("Files: %d  Symbols: %d  Hotspots: %d\n", result.TotalFiles, result.TotalSymbols, len(result.Hotspots))

	if len(result.Hotspots) > 0 && cfg.Verbose {
		fmt.Printf("\n--- Complexity Hotspots ---\n")
		for _, hs := range result.Hotspots {
			fmt.Printf("  %s:%d - %s (CC: %d)\n", hs.File, hs.Line, hs.Symbol, hs.CyclomaticComplexity)
		}
	}

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
	if dryRun {
		fmt.Println("=== DRY RUN MODE - No changes will be applied ===")
	} else {
		if err := checkGitState(path); err != nil {
			return err
		}
	}

	fmt.Printf("Finding duplicate code...\n")

	done := make(chan struct{})
	finished := showSpinner(done, "Finding duplicates", "Deduplication analysis complete")

	mcpManager = sidecar.NewMCPManager(path, cfg)
	plan, err := mcpManager.Deduplicate(path)
	close(done)
	<-finished

	if err != nil {
		return fmt.Errorf("deduplication planning failed: %w", err)
	}

	if dryRun {
		rep := reporter.New(cfg)
		return rep.GenerateDryRun(plan, "deduplicate", path)
	}

	fmt.Printf("\n")
	changeCount := len(plan.Changes)
	if changeCount == 0 {
		fmt.Printf("No duplicate code patterns found.\n")
		return nil
	}

	fmt.Printf("Found %d refactoring opportunity(ies)\n", changeCount)
	if cfg.Verbose {
		fmt.Printf("\n%s\n", plan.Description)
	} else {
		fmt.Printf("\nRun with -v for details.\n")
	}

	if generateReport {
		fmt.Printf("\nSession ID: %s\n", plan.SessionID)
	}

	if !cfg.PreApprove {
		fmt.Printf("\nApply these changes? [y/N]: ")
		var response string
		fmt.Scanln(&response)
		if response != "y" && response != "Y" {
			return fmt.Errorf("aborted by user")
		}
	}

	fmt.Println("\nDeduplication plan generated. Apply functionality coming soon.")

	if generateReport {
		fmt.Printf("\nRun 'reducto report --session %s' to see the full report.\n", plan.SessionID)
	}

	return nil
}

func runIdiomatize(path string, dryRun bool) error {
	if dryRun {
		fmt.Println("=== DRY RUN MODE - No changes will be applied ===")
	} else {
		if err := checkGitState(path); err != nil {
			return err
		}
	}

	fmt.Printf("Finding idiomatization opportunities...\n")

	done := make(chan struct{})
	finished := showSpinner(done, "Analyzing code patterns", "Idiomatization analysis complete")

	mcpManager = sidecar.NewMCPManager(path, cfg)
	plan, err := mcpManager.Idiomatize(path)
	close(done)
	<-finished

	if err != nil {
		return fmt.Errorf("idiomatization planning failed: %w", err)
	}

	if dryRun {
		rep := reporter.New(cfg)
		return rep.GenerateDryRun(plan, "idiomatize", path)
	}

	fmt.Printf("\n")
	changeCount := len(plan.Changes)
	if changeCount == 0 {
		fmt.Printf("No idiomatization opportunities found.\n")
		return nil
	}

	fmt.Printf("Found %d idiomatization opportunity(ies)\n", changeCount)
	if cfg.Verbose {
		fmt.Printf("\n%s\n", plan.Description)
	} else {
		fmt.Printf("\nRun with -v for details.\n")
	}

	if !cfg.PreApprove {
		fmt.Printf("\nApply these changes? [y/N]: ")
		var response string
		fmt.Scanln(&response)
		if response != "y" && response != "Y" {
			return fmt.Errorf("aborted by user")
		}
	}

	fmt.Println("\nIdiomatization plan generated. Apply functionality coming soon.")
	return nil
}

func runPattern(pattern, path string, dryRun bool) error {
	if dryRun {
		fmt.Println("=== DRY RUN MODE - No changes will be applied ===")
	} else {
		if err := checkGitState(path); err != nil {
			return err
		}
	}

	if pattern != "" {
		fmt.Printf("Applying pattern: %s\n", pattern)
	} else {
		fmt.Printf("Finding pattern opportunities...\n")
	}

	done := make(chan struct{})
	finished := showSpinner(done, "Analyzing patterns", "Pattern analysis complete")

	mcpManager = sidecar.NewMCPManager(path, cfg)
	plan, err := mcpManager.ApplyPattern(pattern, path)
	close(done)
	<-finished

	if err != nil {
		return fmt.Errorf("pattern injection failed: %w", err)
	}

	if dryRun {
		rep := reporter.New(cfg)
		return rep.GenerateDryRun(plan, "pattern", path)
	}

	fmt.Printf("\n")
	changeCount := len(plan.Changes)
	if changeCount == 0 {
		fmt.Printf("No pattern opportunities found.\n")
		return nil
	}

	fmt.Printf("Found %d pattern opportunity(ies)\n", changeCount)
	if cfg.Verbose {
		fmt.Printf("\nPattern: %s\n", plan.Pattern)
		fmt.Printf("%s\n", plan.Description)
	} else {
		fmt.Printf("\nRun with -v for details.\n")
	}

	if !cfg.PreApprove {
		fmt.Printf("\nApply these changes? [y/N]: ")
		var response string
		fmt.Scanln(&response)
		if response != "y" && response != "Y" {
			return fmt.Errorf("aborted by user")
		}
	}

	fmt.Println("\nPattern injection plan generated. Apply functionality coming soon.")
	return nil
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

	rootCmd.AddCommand(analyzeCmd)
	rootCmd.AddCommand(deduplicateCmd)
	rootCmd.AddCommand(idiomatizeCmd)
	rootCmd.AddCommand(patternCmd)
	rootCmd.AddCommand(reportCmd)
	rootCmd.AddCommand(versionCmd)
	rootCmd.AddCommand(mcpCmd)
	rootCmd.AddCommand(checkCmd)
}

func init() {
	initCommands()
}
