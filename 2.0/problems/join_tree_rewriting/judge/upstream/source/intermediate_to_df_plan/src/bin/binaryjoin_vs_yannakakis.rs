//! Execute and compare multiple query plans given by their IR format.
//! The executable accepts (a folder with) JSON config file(s).
//! Each config file contains a set of query plans that should produce the same output.

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

#[derive(serde::Deserialize)]
struct QueryConfig {
    /// Query name
    query: String,
    /// Different query plans
    plans: Vec<PlanConfig>,
}

#[derive(serde::Deserialize)]
struct PlanConfig {
    /// Method (e.g. "yannakakis" or "binaryjoin")
    method: String,
    /// Path to the IR query plan (in json format)
    path: PathBuf,
}

#[derive(Parser, Debug, Clone)]
#[command(version, about, long_about = None)]
struct Args {
    /// Folder with JSON query configs, or
    /// path to a single JSON query config.
    #[clap(long, short = 'c', about)]
    configs: PathBuf,

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

    if args.configs.is_file() {
        // Single query config
        let config_path = &args.configs;
        let config: QueryConfig = serde_json::from_reader(std::fs::File::open(config_path)?)?;
        exec_query(
            config,
            config_path,
            args.repetitions,
            args.extra_param_field_names.clone(),
            args.extra_params.clone(),
            &mut csv_wtr,
            &mut catalog,
            &args.outfolder,
        )
        .await?;
    } else if args.configs.is_dir() {
        // Folder with multiple query configs
        let json_files = find_json_files(&args.configs);

        for config_path in json_files {
            let config: QueryConfig = serde_json::from_reader(std::fs::File::open(&config_path)?)?;
            exec_query(
                config,
                &config_path,
                args.repetitions,
                args.extra_param_field_names.clone(),
                args.extra_params.clone(),
                &mut csv_wtr,
                &mut catalog,
                &args.outfolder,
            )
            .await?;
        }
    } else {
        panic!("Invalid path: {:?}", args.configs);
    }

    Ok(())
}

/// Execute query plans given by [QueryConfig].
/// And repeat this `repetitions` times.
async fn exec_query(
    query: QueryConfig,
    config_path: &Path, // path to the config file
    repetitions: usize,
    extra_param_field_names: Vec<String>,
    extra_params: Vec<String>,
    csv_wtr: &mut csv::Writer<std::fs::File>,
    catalog: &mut Catalog,
    outfolder: &Option<PathBuf>,
) -> Result<(), Box<dyn Error>> {
    for _ in 0..repetitions {
        exec_query_once(
            &query,
            config_path,
            extra_param_field_names.clone(),
            extra_params.clone(),
            csv_wtr,
            catalog,
            outfolder,
        )
        .await?;
    }

    Ok(())
}

/// Execute each query plan given by [QueryConfig].
/// Returns whether all query plans produced the same result.
async fn exec_query_once(
    query: &QueryConfig,
    config_path: &Path, // path to the config file
    mut extra_param_field_names: Vec<String>,
    mut extra_params: Vec<String>,
    csv_wtr: &mut csv::Writer<std::fs::File>,
    catalog: &mut Catalog,
    outfolder: &Option<PathBuf>,
) -> Result<bool, Box<dyn Error>> {
    let query_name = &query.query;
    println!("Executing query: {}", query_name);

    // add query name to extra params
    extra_param_field_names.insert(0, "query".into());
    extra_params.insert(0, query_name.to_string());

    let mut results: Vec<String> = Vec::with_capacity(query.plans.len());

    for plan in &query.plans {
        let result = exec_plan(
            plan,
            config_path,
            extra_param_field_names.clone(),
            extra_params.clone(),
            csv_wtr,
            catalog,
            outfolder,
        )
        .await?;
        println!("{}", result);
        results.push(result);
    }

    assert_eq_results(results.as_slice());
    // if !check_eq_results(results.as_slice()) {
    //     println!("Unequal results");
    //     for result in results.iter() {
    //         println!("{}", result);
    //     }
    //     return Ok(false);
    // }

    Ok(true)
}

/// Execute query plan given by [PlanConfig].
async fn exec_plan(
    plan: &PlanConfig,
    config_path: &Path, // path to the config file
    mut extra_param_field_names: Vec<String>,
    mut extra_params: Vec<String>,
    csv_wtr: &mut csv::Writer<std::fs::File>,
    catalog: &mut Catalog,
    outfolder: &Option<PathBuf>,
) -> Result<String, Box<dyn Error>> {
    let plan_path = &plan.path;

    // `plan_path` is relative to `config_path`
    let path = config_path.parent().unwrap().join(plan_path);

    // add method to extra params
    let method = &plan.method;
    extra_param_field_names.insert(0, "method".into());
    extra_params.insert(0, method.to_string());
    extra_param_field_names.insert(1, "variant".into());
    extra_params.insert(1, "flatten".into());

    let task_ctx = catalog.get_state().task_ctx();

    let plan = to_execution_plan(&path, catalog, false).await?;

    let (results, duration) = time_execution(plan.clone(), task_ctx.clone()).await?;

    let result = pretty_format_batches(&results)?.to_string();

    println! {"{}", extra_params.join(", ")}

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
    Ok(result)
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

fn assert_eq_results(results: &[String]) {
    let first = &results[0];
    for result in results.iter() {
        assert_eq!(first, result)
    }
}

// fn check_eq_results(results: &[String]) -> bool {
//     let first = &results[0];
//     for result in results.iter() {
//         if first != result {
//             return false;
//         }
//     }
//     true
// }
