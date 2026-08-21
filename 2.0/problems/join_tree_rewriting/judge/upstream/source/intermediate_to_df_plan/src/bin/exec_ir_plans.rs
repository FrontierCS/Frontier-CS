//! Execute query plans specified by their IR (intermediate representation) format.

use std::{
    error::Error,
    fs,
    path::{Path, PathBuf},
    time::Duration,
};

use clap::Parser;
use datafusion::{
    arrow::util::pretty::pretty_format_batches,
    prelude::{SessionConfig, SessionContext},
};
use intermediate_to_df_plan::{
    time_execution, to_execution_plan,
    util::{metrics, yann_detailed_metrics, Catalog},
};

#[derive(Parser, Debug, Clone)]
#[command(version, about, long_about = None)]
struct Args {
    /// Folder with JSON query plans, or
    /// path to a single JSON query plan.
    /// If folder is given, the plans can be in any subfolder at any depth.
    #[clap(long, short = 'p', about)]
    plans: PathBuf,

    /// Folder with Parquet data for all relations.
    #[clap(long, short = 'd', about)]
    data: PathBuf,

    #[clap(long, short = 'b', default_value_t = 8192)]
    batch_size: usize,

    /// Path to *non-existing* output folder.
    /// If Some, folder will be created and metrics will be written to it.
    #[clap(long, short = 'o', about)]
    pub outfolder: Option<PathBuf>,

    /// Path to *existing* csv file to write timings to.
    #[clap(long, short = 't', about)]
    pub timings_outfile: PathBuf,

    /// Extra parameters that also need to be written to each record in `timings_outfile` or the JSON metrics in the `outfolder`.
    /// They are not used in the program.
    #[clap(long, short = 'e', about)]
    pub extra_params: Vec<String>,

    /// Names for the `extra_params` parameters, used in the JSON metrics in the `outfolder`.
    /// Need to be of same length as `extra_params`
    /// They are not used in the program.
    #[clap(long, short = 'f', about)]
    pub extra_param_field_names: Vec<String>,

    /// Number of times to execute each query plan.
    #[clap(long, short = 'r', default_value_t = 1)]
    pub repetitions: usize,

    /// Queries to skip
    #[clap(long, short = 's')]
    pub skip: Vec<String>,

    /// Resume from query
    #[clap(long)]
    pub resume: Option<String>,
}

// Single threaded, also known as "current_thread" runtime in Tokio
// src: https://docs.rs/tokio/latest/tokio/attr.main.html#using-current-thread-runtime
//#[tokio::main(flavor = "multi_thread", worker_threads = 1)]
#[tokio::main(flavor = "current_thread")]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Args = Args::parse();

    // Create output folder & files
    let mut csv_wtr = csv::Writer::from_writer(
        std::fs::OpenOptions::new()
            .append(true)
            .open(&args.timings_outfile)?,
    );

    // Init sessioncontext and register all relations
    let ctx = SessionContext::new_with_config(
        SessionConfig::new()
            .with_batch_size(args.batch_size)
            .with_target_partitions(1),
    );

    let mut catalog = Catalog::new_with_context(ctx);
    catalog.add_parquets(&args.data, args.batch_size).await;

    if args.plans.is_file() {
        // Execute single plan
        exec_plan(
            args.plans,
            args.repetitions,
            &mut args.extra_param_field_names.clone(),
            &mut args.extra_params.clone(),
            &mut csv_wtr,
            &mut catalog,
            &args.outfolder,
        )
        .await?;
    } else if args.plans.is_dir() {
        // Execute all plans in folder
        let mut resume = args.resume.is_none();
        let resume_from = args.resume.unwrap_or("".to_string());

        for path in find_json_files(&args.plans) {
            let path_str = path.to_str().unwrap();
            if path_str.contains("run_") && !path_str.contains("run_1.json") {
                continue;
            }

            if !resume {
                // check if we can resume from this file
                if path_str.contains(&format!("/{}", resume_from)) {
                    resume = true;
                }
                println!("Skipping file: {:?}", path);
                continue;
            }
            if args
                .skip
                .iter()
                .any(|s| path_str.contains(&format!("/{}", s)))
            {
                println!("Skipping file: {:?}", path);
                continue;
            }

            exec_plan(
                path,
                args.repetitions,
                &mut args.extra_param_field_names.clone(),
                &mut args.extra_params.clone(),
                &mut csv_wtr,
                &mut catalog,
                &args.outfolder,
            )
            .await?;
        }
    } else {
        panic!("Invalid path: {:?}", args.plans);
    }

    Ok(())
}

async fn exec_plan(
    path: PathBuf,
    repetitions: usize,
    extra_param_field_names: &mut Vec<String>,
    extra_params: &mut Vec<String>,
    csv_wtr: &mut csv::Writer<std::fs::File>,
    catalog: &mut Catalog,
    outfolder: &Option<PathBuf>,
) -> Result<(), Box<dyn Error>> {
    println!("Processing file: {:?}", path);

    let task_ctx = catalog.get_state().task_ctx();

    for rep in 0..repetitions {
        let plan = to_execution_plan(&path, catalog, false).await?;

        // print execution plan
        // let display_plan = displayable(plan.as_ref()).set_show_statistics(true);
        // println!("{}", display_plan.indent(true));

        let (results, duration) = time_execution(plan.clone(), task_ctx.clone()).await?;

        println!("{}", pretty_format_batches(&results)?.to_string());
        println!("Execution time: {:?}", duration);

        let mut extra_param_field_names = extra_param_field_names.clone();
        extra_param_field_names.insert(0, "path".into());
        extra_param_field_names.insert(1, "repetition".into());
        let mut extra_params = extra_params.clone();
        extra_params.insert(0, format!("{}", path.to_str().unwrap()));
        extra_params.insert(1, rep.to_string());

        write_timings(csv_wtr, &extra_params, duration)?;

        if let Some(outfolder) = outfolder {
            // write metrics generated by DataFusion
            write_metrics(
                &outfolder.join("metrics.txt"),
                &metrics(&plan),
                &extra_params[..],
                &extra_param_field_names[..],
            )?;
            // If the plan contains a Yannakakis node, write its detailed metrics (groupby & semijoins)
            let yann_metrics = yann_detailed_metrics(&plan);
            if yann_metrics.is_some() {
                write_metrics(
                    &outfolder.join("yannakakis_metrics.txt"),
                    &yann_metrics.unwrap(),
                    &extra_params[..],
                    &extra_param_field_names[..],
                )?;
            }
        }
    }
    Ok(())
}

/// Write record to existing csv file with given timings (as µs).
fn write_timings<W: std::io::Write>(
    csv_wtr: &mut csv::Writer<W>,
    extra_params: &Vec<String>,
    duration: Duration,
) -> Result<(), csv::Error> {
    if extra_params.is_empty() {
        csv_wtr.write_record(&[&duration.as_micros().to_string()])?;
    } else {
        // extra_params is not empty
        // write extra_params as separate columns
        let mut record: Vec<String> = vec![duration.as_micros().to_string()];
        record.extend(extra_params.iter().cloned());
        csv_wtr.write_record(&record)?;
    }

    Ok(())
}

/// Create `file` if it does not exist and write `metrics` to it, appending if the file existed.
fn write_metrics(
    file: &PathBuf,
    metrics: &str,
    extra_params: &[String],
    extra_param_field_names: &[String],
) -> Result<(), std::io::Error> {
    use std::fmt::Write;
    use std::fs::OpenOptions;
    use std::io::Write as OtherWrite;

    std::fs::create_dir_all(file.parent().unwrap())?;

    let mut file = OpenOptions::new().create(true).append(true).open(file)?;

    // Add the extra_params to the JSON metrics
    let mut output: String = String::with_capacity(10_000);

    write!(output, "{{ \"params\": ").expect("Error writing metrics to string.");

    if extra_params.is_empty() {
        write!(output, "null").expect("Error writing metrics to string.");
    } else {
        write!(output, "{{").expect("Error writing metrics to string.");
        for (param_value, field_name) in extra_params.iter().zip(extra_param_field_names.iter()) {
            write!(output, " \"{}\": \"{}\",", field_name, param_value)
                .expect("Error writing metrics to string.");
        }
        // Remove the trailing comma
        output.pop();
        write!(output, "}}").expect("Error writing metrics to string.");
    }

    writeln!(output, ", \"plan\": {} }}", metrics).expect("Error writing metrics to string.");

    file.write_all(output.as_bytes())?;

    Ok(())
}

/// Find all .json files in the given directory (recursively).
fn find_json_files(dir: &Path) -> Vec<PathBuf> {
    let mut json_files = Vec::new();

    // Check if the path is a directory
    if dir.is_dir() {
        // Iterate over the directory contents
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries {
                if let Ok(entry) = entry {
                    let path = entry.path();

                    // If it's a directory, recurse
                    if path.is_dir() {
                        let mut subdir_files = find_json_files(&path);
                        json_files.append(&mut subdir_files);
                    } else {
                        // If it's a .json file, add it to the list
                        if let Some(ext) = path.extension() {
                            if ext == "json" {
                                json_files.push(path);
                            }
                        }
                    }
                }
            }
        }
    }

    json_files
}
