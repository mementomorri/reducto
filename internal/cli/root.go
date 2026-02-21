package cli

import (
	"fmt"
	"os"

	"github.com/alexkarsten/reducto/internal/config"
	"github.com/alexkarsten/reducto/internal/git"
	"github.com/alexkarsten/reducto/internal/reporter"
	"github.com/alexkarsten/reducto/internal/sidecar"
	"github.com/alexkarsten/reducto/pkg/models"
	"github.com/spf13/cobra"
)

var (
	cfgFile    string
	cfg        *models.Config
	mcpManager *sidecar.MCPManager
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

		return nil
	},
}

func init() {
	rootCmd.PersistentFlags().StringVarP(&cfgFile, "config", "c", "", "config file (default is $HOME/.reducto.yaml)")
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

func runAnalyze(path string) error {
	fmt.Printf("Analyzing repository: %s\n", path)

	if err := checkGitState(path); err != nil {
		return err
	}

	mcpManager = sidecar.NewMCPManager(path, cfg)
	result, err := mcpManager.Analyze(path)
	if err != nil {
		return fmt.Errorf("analysis failed: %w", err)
	}

	fmt.Printf("\n=== Analysis Results ===\n")
	fmt.Printf("Total files: %d\n", result.TotalFiles)
	fmt.Printf("Total symbols: %d\n", result.TotalSymbols)
	fmt.Printf("Complexity hotspots: %d\n", len(result.Hotspots))

	if len(result.Hotspots) > 0 {
		fmt.Printf("\n--- Complexity Hotspots ---\n")
		for _, hs := range result.Hotspots {
			fmt.Printf("  %s:%d - %s (CC: %d)\n", hs.File, hs.Line, hs.Symbol, hs.CyclomaticComplexity)
		}
	}

	return nil
}

func runDeduplicate(path string, commitChanges bool) error {
	fmt.Printf("Running deduplication: %s\n", path)

	if err := checkGitState(path); err != nil {
		return err
	}

	mcpManager = sidecar.NewMCPManager(path, cfg)
	plan, err := mcpManager.Deduplicate(path)
	if err != nil {
		return fmt.Errorf("deduplication planning failed: %w", err)
	}

	fmt.Printf("\n=== Refactoring Plan ===\n")
	fmt.Printf("%s\n", plan.Description)

	if !cfg.PreApprove {
		fmt.Printf("\nApply these changes? [y/N]: ")
		var response string
		fmt.Scanln(&response)
		if response != "y" && response != "Y" {
			return fmt.Errorf("aborted by user")
		}
	}

	fmt.Println("\nDeduplication plan generated. Apply functionality coming soon.")
	return nil
}

func runIdiomatize(path string) error {
	fmt.Printf("Running idiomatization: %s\n", path)

	if err := checkGitState(path); err != nil {
		return err
	}

	mcpManager = sidecar.NewMCPManager(path, cfg)
	plan, err := mcpManager.Idiomatize(path)
	if err != nil {
		return fmt.Errorf("idiomatization planning failed: %w", err)
	}

	fmt.Printf("\n=== Idiomatization Plan ===\n")
	fmt.Printf("%s\n", plan.Description)

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

func runPattern(pattern, path string) error {
	fmt.Printf("Applying design pattern: %s\n", pattern)
	fmt.Printf("Path: %s\n", path)

	if err := checkGitState(path); err != nil {
		return err
	}

	mcpManager = sidecar.NewMCPManager(path, cfg)
	plan, err := mcpManager.ApplyPattern(pattern, path)
	if err != nil {
		return fmt.Errorf("pattern injection failed: %w", err)
	}

	fmt.Printf("\n=== Pattern Injection Plan ===\n")
	fmt.Printf("Pattern: %s\n", plan.Pattern)
	fmt.Printf("%s\n", plan.Description)

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

		return runDeduplicate(path, commitChanges)
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

		return runIdiomatize(path)
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

		return runPattern(pattern, path)
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

func initCommands() {
	analyzeCmd.Flags().Bool("report", false, "generate report after analysis")
	deduplicateCmd.Flags().BoolP("yes", "y", false, "skip approval and apply changes automatically")
	deduplicateCmd.Flags().Bool("commit", false, "commit changes to git after successful refactoring")
	idiomatizeCmd.Flags().BoolP("yes", "y", false, "skip approval and apply changes automatically")
	patternCmd.Flags().BoolP("yes", "y", false, "skip approval and apply changes automatically")
	reportCmd.Flags().StringP("session", "s", "", "session ID to report (default: last session)")

	rootCmd.AddCommand(analyzeCmd)
	rootCmd.AddCommand(deduplicateCmd)
	rootCmd.AddCommand(idiomatizeCmd)
	rootCmd.AddCommand(patternCmd)
	rootCmd.AddCommand(reportCmd)
	rootCmd.AddCommand(versionCmd)
}

func init() {
	initCommands()
}
