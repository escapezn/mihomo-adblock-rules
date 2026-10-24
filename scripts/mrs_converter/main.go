package main

import (
	"flag"
	"fmt"
	"os"
	"strings"

	P "github.com/metacubex/mihomo/constant/provider"
	"github.com/metacubex/mihomo/rules/provider"
)

func main() {
	inPath := flag.String("in", "", "Input file path (.yaml or .list/.txt)")
	outPath := flag.String("out", "", "Output .mrs file path")
	flag.Parse()

	if *inPath == "" || *outPath == "" {
		fmt.Println("Usage: mrs_converter -in <input_path> -out <output_path>")
		os.Exit(1)
	}

	buf, err := os.ReadFile(*inPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to read file %s: %v\n", *inPath, err)
		os.Exit(1)
	}

	format := P.TextRule
	if strings.HasSuffix(*inPath, ".yaml") || strings.HasSuffix(*inPath, ".yml") {
		format = P.YamlRule
	}

	outFile, err := os.Create(*outPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to create output file %s: %v\n", *outPath, err)
		os.Exit(1)
	}
	defer outFile.Close()

	err = provider.ConvertToMrs(buf, P.Domain, format, outFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to convert to mrs: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Successfully converted %s to %s\n", *inPath, *outPath)
}
