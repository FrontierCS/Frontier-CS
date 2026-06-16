import fs from 'fs/promises';
import path from 'path';
import { toNs, toBytes, fileExists } from './utils.js';
import { GoJudgeClient } from './gojudge.js';
import { ProblemManager } from './problem_manager.js';

export class JudgeEngine {
    constructor(config) {
        this.problemManager = new ProblemManager({
            problemsRoot: config.problemsRoot,
            gjAddr: config.gjAddr,
            testlibPath: config.testlibPath
        });
        this.goJudge = new GoJudgeClient(config.gjAddr);
        this.submissionManager = config.submissionManager;
        this.testlibPath = config.testlibPath || '/lib/testlib';
        this.saveOutputs = process.env.SAVE_OUTPUTS === 'true';

        // In-memory queue and results
        this.queue = [];
        this.results = new Map();

        // Cache for compiled checkers/interactors (pid -> { checkerId, interactorId })
        // Avoids recompiling the same checker for every submission
        this.checkerCache = new Map();
        this.checkerCompiling = new Map();  // pid -> Promise (for concurrent compile protection)

        // Start worker threads
        this.startWorkers(config.workers || 4);
    }

    // Get or compile checker with caching
    async getOrCompileChecker(pid, problem) {
        // Check cache first
        if (this.checkerCache.has(pid)) {
            return this.checkerCache.get(pid);
        }

        // Check if another worker is already compiling this checker
        if (this.checkerCompiling.has(pid)) {
            return await this.checkerCompiling.get(pid);
        }

        // Start compiling and store the promise
        const compilePromise = this._compileChecker(pid, problem);
        this.checkerCompiling.set(pid, compilePromise);

        try {
            const result = await compilePromise;
            this.checkerCache.set(pid, result);
            return result;
        } finally {
            this.checkerCompiling.delete(pid);
        }
    }

    async _compileChecker(pid, problem) {
        const checkerBinPath = path.join(problem.pdir, `${problem.checker}.bin`);

        if (await fileExists(checkerBinPath)) {
            const result = await this.goJudge.copyInBin(checkerBinPath);
            return { checkerId: result.binId, cleanup: null };  // Don't cleanup cached checkers
        } else if (problem.checker) {
            const chkSrc = await this.problemManager.readCheckerSource(pid, problem.checker);
            const result = await this.goJudge.prepareChecker(chkSrc, this.testlibPath);
            return { checkerId: result.checkerId, cleanup: null };  // Don't cleanup cached checkers
        }

        throw new Error(`No checker found for problem ${pid}`);
    }

    // Get or compile interactor with caching
    async getOrCompileInteractor(pid, problem) {
        const cacheKey = `interactor:${pid}`;

        if (this.checkerCache.has(cacheKey)) {
            return this.checkerCache.get(cacheKey);
        }

        if (this.checkerCompiling.has(cacheKey)) {
            return await this.checkerCompiling.get(cacheKey);
        }

        const compilePromise = this._compileInteractor(pid, problem);
        this.checkerCompiling.set(cacheKey, compilePromise);

        try {
            const result = await compilePromise;
            this.checkerCache.set(cacheKey, result);
            return result;
        } finally {
            this.checkerCompiling.delete(cacheKey);
        }
    }

    async _compileInteractor(pid, problem) {
        const interactorBinPath = path.join(problem.pdir, `${problem.interactor}.bin`);

        if (await fileExists(interactorBinPath)) {
            const result = await this.goJudge.copyInBin(interactorBinPath);
            return { interactorId: result.binId, cleanup: null };
        } else if (problem.interactor) {
            const interSrc = await this.problemManager.readInteractorSource(pid, problem.interactor);
            const result = await this.goJudge.prepareInteractor(interSrc, this.testlibPath);
            return { interactorId: result.interactorId, cleanup: null };
        }

        throw new Error(`No interactor found for problem ${pid}`);
    }

    // Submit a task
    async submit(pid, lang, code) {
        const sid = await this.submissionManager.nextSubmissionId();
        this.results.set(sid, { status: 'queued' });
        const { bucketDir, subDir } = this.submissionManager.submissionPaths(sid);
        await fs.mkdir(bucketDir, { recursive: true });
        await fs.mkdir(subDir, { recursive: true });

        if(this.queue.length >= 1024 * 512){
            this.queue.push({ sid, pid, lang });
            await fs.writeFile(
                path.join(subDir, `source.code`),
                code
            );
        }else{
            this.queue.push({ sid, pid, lang, code });
        }

        await fs.writeFile(
            path.join(subDir, 'meta.json'), 
            JSON.stringify({ sid, pid, lang, ts: Date.now() }, null, 2)
        );

        return sid;
    }

    // Get the result
    getResult(sid) {
        const r = this.results.get(sid);
        if (r) {
            // Only delete the result from the cache if it's a final state
            if (r.status === 'done' || r.status === 'error') {
                this.results.delete(sid);
            }
            return r;
        }

        try {
            const { subDir } = this.submissionManager.submissionPaths(sid);
            const txt = fs.readFileSync(path.join(subDir, 'result.json'), 'utf8');
            return JSON.parse(txt);
        } catch {
            return null;
        }
    }

    // Clear the results cache
    clearResults() {
        this.results.clear();
    }

    // Judge a single test case
    async judgeCase({ runSpec, caseItem, problem, checkerId }) {
        // Read input and answer files
        const inf = await this.problemManager.readTestFile(problem.pdir.split('/').pop(), caseItem.input);
        
        let ans;
        try {
            const ansFile = caseItem.output.replace(/\.out$/, '.ans');
            ans = await this.problemManager.readTestFile(problem.pdir.split('/').pop(), ansFile);
        } catch {
            ans = await this.problemManager.readTestFile(problem.pdir.split('/').pop(), caseItem.output);
        }

        // Run the contestant's program
        const runRes = await this.goJudge.runOne({
            args: runSpec.runArgs,
            env: ['PATH=/usr/bin:/bin'],
            files: [{ content: inf }, { name: 'stdout', max: 128 * 1024 * 1024 }, { name: 'stderr', max: 64 * 1024 * 1024 }],
            cpuLimit: toNs(caseItem.time),
            clockLimit: toNs(caseItem.time) * 2,
            memoryLimit: toBytes(caseItem.memory),
            stackLimit: toBytes(caseItem.memory),
            addressSpaceLimit: true,
            procLimit: 128,
            copyIn: { ...runSpec.preparedCopyIn }
        });

        let extra = '';
        if (runRes.status === 'Signalled') {
            extra = `(signal=${runRes.error || 'unknown'})`;
        }

        if (runRes.status !== 'Accepted') {
            return { 
                ok: false, 
                status: runRes.status, 
                time: runRes.runTime, 
                memory: runRes.memory, 
                msg: (runRes.files?.stderr || '' ) + extra
            };
        }

        const out = runRes.files?.stdout ?? '';
        
        // Run the checker (testlib)
        const chkRes = await this.goJudge.runOne({
            args: ['chk', 'in.txt', 'out.txt', 'ans.txt'],
            env: ['PATH=/usr/bin:/bin'],
            files: [{ content: '' }, { name: 'stdout', max: 1024 * 1024 }, { name: 'stderr', max: 1024 * 1024 }],
            cpuLimit: 10e9, // 10 seconds
            clockLimit: 20e9,
            memoryLimit: 256 << 20,
            stackLimit: 256 << 20,
            procLimit: 128,
            copyIn: {
                'chk': { fileId: checkerId },
                'in.txt': { content: inf },
                'out.txt': { content: out },
                'ans.txt': { content: ans }
            }
        });

        const ok = chkRes.status === 'Accepted' && chkRes.exitStatus === 0;
        return {
            ok,
            status: ok ? 'Accepted' : 'Wrong Answer',
            time: runRes.runTime,
            memory: runRes.memory,
            msg: chkRes.files?.stdout || chkRes.files?.stderr || '',
            output: out
        };
    }

    async judgeInteractiveCase({ runSpec, caseItem, problem, interactorId }) {
        const inf = await this.problemManager.readTestFile(problem.pdir.split('/').pop(), caseItem.input);
        
        let ans;
        try {
            const ansFile = caseItem.output.replace(/\.out$/, '.ans');
            ans = await this.problemManager.readTestFile(problem.pdir.split('/').pop(), ansFile);
        } catch {
            ans = await this.problemManager.readTestFile(problem.pdir.split('/').pop(), caseItem.output);
        }

        // Run interactive judging
        const interactRes = await this.goJudge.run({
            cmd: [
                { // Contestant's program
                    args: runSpec.runArgs,
                    env: ['PATH=/usr/bin:/bin'],
                    files: [null, null, { name: 'stderr', max: 1024*1024 }],
                    cpuLimit: toNs(caseItem.time),
                    clockLimit: toNs(caseItem.time) * 2,
                    memoryLimit: toBytes(caseItem.memory),
                    stackLimit: toBytes(caseItem.memory),
                    procLimit: 128,
                    copyIn: { ...runSpec.preparedCopyIn },
                },
                { // Interactor
                    args: ['interactor', 'in.txt', 'tout.txt', 'ans.txt'],
                    env: ['PATH=/usr/bin:/bin'],
                    files: [null, null, { name: 'stderr', max: 1024*1024 }],
                    cpuLimit: toNs(caseItem.time) * 4,
                    clockLimit: toNs(caseItem.time) * 4 * 2,
                    memoryLimit: toBytes(caseItem.memory) * 4,
                    stackLimit: toBytes(caseItem.memory) * 4,
                    procLimit: 128,
                    copyIn: {
                        'interactor': { fileId: interactorId },
                        'in.txt': { content: inf },
                        'ans.txt': { content: ans }
                    }
                }
            ],
            pipeMapping: [
                { in:  { index: 0, fd: 1 }, out: { index: 1, fd: 0 } },
                { in:  { index: 1, fd: 1 }, out: { index: 0, fd: 0 } }
            ]
        });

        const submissionRes = interactRes[0];
        const interactorRes = interactRes[1];

        if (submissionRes.status === 'Accepted' && interactorRes.status === 'Accepted' && interactorRes.exitStatus === 0 && submissionRes.exitStatus === 0 ) {
            return {
                ok: true,
                status: 'Accepted',
                time: submissionRes.runTime,
                memory: Math.max(submissionRes.memory, interactorRes.memory),
                msg: (interactorRes.files?.stdout || '') + (interactorRes.files?.stderr || '')
            };
        }
        if (submissionRes.status !== 'Accepted') {
            let extra = (submissionRes.status === 'Signalled') ? ` (signal=${submissionRes.error || 'unknown'})` : '';
            return { ok: false, status: submissionRes.status, time: submissionRes.runTime, memory: submissionRes.memory, msg: (submissionRes.files?.stderr || '') + extra };
        }
        if (interactorRes.status !== 'Accepted') {
            return { ok: false, status: interactorRes.status, time: submissionRes.runTime, memory: submissionRes.memory, msg: (interactorRes.files?.stderr || '') };
        }
        // Default to WA if interactor exits non-zero
        return { ok: false, status: 'Wrong Answer', time: submissionRes.runTime, memory: submissionRes.memory, msg: (interactorRes.files?.stderr || '') };
    }

    // Start worker threads
    startWorkers(workerCount) {
        for (let i = 0; i < workerCount; i++) {
            this.startWorker();
        }
    }

    async judgeDefault(problem, sid, pid, lang, code, subDir) {
        let cleanupIds = [];
        try {
            // Prepare contestant's program
            const runSpec = await this.goJudge.prepareProgram({ lang, code, mainName: problem.filename || null });
            cleanupIds.push(...(runSpec.cleanupIds || []));

            // Get cached or compile checker (with concurrent compile protection)
            const { checkerId } = await this.getOrCompileChecker(pid, problem);

            // Run all cases
            // let totalScore = 0;
            // let totalScoreUnbounded = 0;
            // const caseResults = [];
            // for (const c of problem.cases) {
            //     const r = await this.judgeCase({ runSpec, caseItem: c, problem, checkerId });
                
            //     const matchBounded = r.msg.match(/Ratio: ([\d.]+)/);
            //     const matchUnbounded = r.msg.match(/RatioUnbounded: ([\d.]+)/);
                
            //     r.scoreRatio = matchBounded ? parseFloat(matchBounded[1]) : (r.ok ? 1.0 : 0);
            //     r.scoreRatioUnbounded = matchUnbounded ? parseFloat(matchUnbounded[1]) : r.scoreRatio;
                
            //     totalScore += r.scoreRatio;
            //     totalScoreUnbounded += r.scoreRatioUnbounded;
            //     caseResults.push(r);
            // }
            
            const casePromises = problem.cases.map(async (c) => {
                const r = await this.judgeCase({ runSpec, caseItem: c, problem, checkerId });

                const matchBounded = r.msg.match(/Ratio: ([\d.]+)/);
                const matchUnbounded = r.msg.match(/RatioUnbounded: ([\d.]+)/);

                r.scoreRatio = matchBounded ? parseFloat(matchBounded[1]) : (r.ok ? 1.0 : 0);
                r.scoreRatioUnbounded = matchUnbounded ? parseFloat(matchUnbounded[1]) : r.scoreRatio;

                return r;
            });

            const caseResults = await Promise.all(casePromises);

            // Aggregate
            let totalScore = 0;
            let totalScoreUnbounded = 0;
            for (const r of caseResults) {
                totalScore += r.scoreRatio;
                totalScoreUnbounded += r.scoreRatioUnbounded;
            }



            // The overall "passed" status depends on all cases achieving a perfect score ratio
            const passed = caseResults.every(r => r.scoreRatio === 1.0);
            const overallResult = passed ? 'Correct Answer' : 'Wrong Answer';
            const finalScore = problem.cases.length > 0 ? (totalScore / problem.cases.length) * 100 : 0;
            const finalScoreUnbounded = problem.cases.length > 0 ? (totalScoreUnbounded / problem.cases.length) * 100 : 0;

            // Remap individual case statuses based on scoreRatio
            const finalCases = caseResults.map(caseResult => ({
                ...caseResult,
                status: caseResult.scoreRatio === 1.0 ? 'Correct' : 'Wrong Answer'
            }));

            const final = { 
                status: 'done', 
                passed, 
                result: overallResult, 
                score: finalScore, 
                scoreUnbounded: finalScoreUnbounded,
                cases: finalCases 
            };
            this.results.set(sid, final);
            await fs.writeFile(path.join(subDir, 'result.json'), JSON.stringify(final, null, 2));
            
            // Save outputs if enabled
            if (this.saveOutputs) {
                for (let i = 0; i < caseResults.length; i++) {
                    if (caseResults[i].output !== undefined) {
                        await fs.writeFile(path.join(subDir, `case_${i + 1}.out`), caseResults[i].output);
                    }
                }
            }
        } catch (e) {
            const err = { status: 'error', error: String(e) };
            this.results.set(sid, err);
            await fs.writeFile(path.join(subDir, 'result.json'), JSON.stringify(err, null, 2));
        } finally {
            // Only cleanup contestant's program, not the cached checker
            for (const id of cleanupIds) await this.goJudge.deleteFile(id);
        }
    }

    async judgeInteractive(problem, sid, pid, lang, code, subDir) {
        let cleanupIds = [];
        try {
            // Prepare program
            const runSpec = await this.goJudge.prepareProgram({ lang, code, mainName: problem.filename || null });
            cleanupIds.push(...(runSpec.cleanupIds || []));

            // Get cached or compile interactor (with concurrent compile protection)
            const { interactorId } = await this.getOrCompileInteractor(pid, problem);

            // Run all cases and calculate score
            // let totalScore = 0;
            // let totalScoreUnbounded = 0;
            // const caseResults = [];
            // for (const c of problem.cases) {
            //     const r = await this.judgeInteractiveCase({ runSpec, caseItem: c, problem, interactorId });
                
            //     // Parse score ratio from interactor message
            //     const matchBounded = r.msg.match(/Ratio: ([\d.]+)/);
            //     const matchUnbounded = r.msg.match(/RatioUnbounded: ([\d.]+)/);
                
            //     r.scoreRatio = matchBounded ? parseFloat(matchBounded[1]) : (r.ok ? 1.0 : 0);
            //     r.scoreRatioUnbounded = matchUnbounded ? parseFloat(matchUnbounded[1]) : r.scoreRatio;
                
            //     totalScore += r.scoreRatio;
            //     totalScoreUnbounded += r.scoreRatioUnbounded;
            //     caseResults.push(r);
            // }

            const casePromises = problem.cases.map(async (c) => {
                const r = await this.judgeInteractiveCase({ runSpec, caseItem: c, problem, interactorId });

                const matchBounded = r.msg.match(/Ratio: ([\d.]+)/);
                const matchUnbounded = r.msg.match(/RatioUnbounded: ([\d.]+)/);

                r.scoreRatio = matchBounded ? parseFloat(matchBounded[1]) : (r.ok ? 1.0 : 0);
                r.scoreRatioUnbounded = matchUnbounded ? parseFloat(matchUnbounded[1]) : r.scoreRatio;

                return r;
            });

            const caseResults = await Promise.all(casePromises);

            let totalScore = 0;
            let totalScoreUnbounded = 0;
            for (const r of caseResults) {
                totalScore += r.scoreRatio;
                totalScoreUnbounded += r.scoreRatioUnbounded;
            }

            const passed = caseResults.every(r => r.scoreRatio === 1.0);
            const overallResult = passed ? 'Correct Answer' : 'Wrong Answer';
            const finalScore = problem.cases.length > 0 ? (totalScore / problem.cases.length) * 100 : 0;
            const finalScoreUnbounded = problem.cases.length > 0 ? (totalScoreUnbounded / problem.cases.length) * 100 : 0;

            // Remap individual case statuses for clarity
            const finalCases = caseResults.map(caseResult => ({
                ...caseResult,
                status: caseResult.scoreRatio === 1.0 ? 'Correct' : 'Wrong Answer'
            }));

            const final = { 
                status: 'done', 
                passed, 
                result: overallResult, 
                score: finalScore, 
                scoreUnbounded: finalScoreUnbounded,
                cases: finalCases 
            };
            this.results.set(sid, final);
            await fs.writeFile(path.join(subDir, 'result.json'), JSON.stringify(final, null, 2));
            
            // Save outputs if enabled
            if (this.saveOutputs) {
                for (let i = 0; i < caseResults.length; i++) {
                    if (caseResults[i].output !== undefined) {
                        await fs.writeFile(path.join(subDir, `case_${i + 1}.out`), caseResults[i].output);
                    }
                }
            }
        } catch (e) {
            const err = { status: 'error', error: String(e) };
            this.results.set(sid, err);
            await fs.writeFile(path.join(subDir, 'result.json'), JSON.stringify(err, null, 2));
        } finally {
            // Only cleanup contestant's program, not the cached interactor
            for (const id of cleanupIds) await this.goJudge.deleteFile(id);
        }
    }

    // A single worker thread
    async startWorker() {
        while (true) {
            const job = this.queue.shift();
            if (!job) { 
                await new Promise(r => setTimeout(r, 50)); 
                continue; 
            }

            let { sid, pid, lang, code } = job;
            const { subDir } = this.submissionManager.submissionPaths(sid);
            if (typeof code !== 'string') {
                code = await fs.readFile(path.join(subDir, 'source.code'), 'utf8');
            } else {
                await fs.writeFile(path.join(subDir, 'source.code'), code);
            }
            
            const problem = await this.problemManager.loadProblem(pid);

            switch (problem.cfg.type) {
                case 'interactive':
                    await this.judgeInteractive(problem, sid, pid, lang, code, subDir);
                    break;
                case 'leetcode':
                    throw new Error('LeetCode problems are not supported for now.');
                default:
                    await this.judgeDefault(problem, sid, pid, lang, code, subDir);
                    break;
            }
        }
    }

    getSourceFileName(lang) {
        switch (lang) {
            case 'cpp': return 'main.cpp';
            case 'py':
            case 'pypy': return 'main.py';
            case 'java': return 'Main.java';
            default: return 'main.txt';
        }
    }
}
