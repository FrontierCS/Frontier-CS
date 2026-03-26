import fs from 'fs/promises';
import path from 'path';

// Empty directory
export async function emptyDir(dir) {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        await fs.rm(fullPath, { recursive: true, force: true });
    }
}

// Time unit conversion
export function toNs(s) {
    if (typeof s === 'number') return s;
    const m = String(s).match(/^([\d.]+)\s*(ms|s)?$/i);
    const v = parseFloat(m?.[1] ?? '0'); 
    const u = (m?.[2] || 's').toLowerCase();
    return Math.round(v * (u === 'ms' ? 1e6 : 1e9));
}

// Memory unit conversion
export function toBytes(s) {
    if (typeof s === 'number') return s;
    const m = String(s).match(/^([\d.]+)\s*(k|m|g|)$|^([\d.]+)$/i);
    const v = parseFloat(m?.[1] ?? m?.[3] ?? '0'); 
    const u = (m?.[2] || '').toLowerCase();
    const mul = u === 'g' ? 1 << 30 : u === 'm' ? 1 << 20 : u === 'k' ? 1 << 10 : 1;
    return Math.round(v * mul);
}

export async function dirExists(pdir) {
  try {
    await fs.access(pdir);
    return true;              // Can access -> exists
  } catch (e) {
    if (e && e.code === 'ENOENT') return false; // Doesn't exist
    throw e;                  // Other IO errors are thrown up (to unified error handler)
  }
}

export async function fileExists(filePath) {
    try {
        await fs.stat(filePath);
        return true;
    } catch {
        return false;
    }
}

export async function ensureDir(dirPath) {
    try {
        await fs.mkdir(dirPath, { recursive: true });
    } catch (err) {
        if (err.code !== 'EEXIST') throw err;
    }
}

export async function parseProblemConf(confPath) {
    const content = await fs.readFile(confPath, 'utf8');
    const lines = content.split('\n');
    const conf = {};
    
    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) continue;
        
        const [key, ...valueParts] = trimmed.split(/\s+/);
        const value = valueParts.join(' ');
        
        if (key && value) {
            conf[key.toLowerCase()] = value;
        }
    }
    
    return conf;
}

export async function findTestCases(dir) {
        const files = await fs.readdir(dir);
        const testCases = new Map();

        // Find all .in files
        for (const file of files) {
            if (file.endsWith('.in')) {
                const baseName = file.slice(0, -3);
                testCases.set(baseName, { input: file, output: null });
            }
        }

        // Find corresponding .ans or .out files
        for (const file of files) {
            if (file.endsWith('.ans') || file.endsWith('.out')) {
                const baseName = file.endsWith('.ans') ? file.slice(0, -4) : file.slice(0, -4);
                if (testCases.has(baseName)) {
                    testCases.get(baseName).output = file;
                }
            }
        }

        // Filter out complete test case pairs
        const validCases = [];
        for (const [baseName, caseFiles] of testCases) {
            if (caseFiles.input && caseFiles.output) {
                validCases.push({
                    baseName,
                    input: caseFiles.input,
                    output: caseFiles.output
                });
            }
        }

        // Sort by lexicographical order
        validCases.sort((a, b) => a.baseName.localeCompare(b.baseName));
        return validCases;
    }

export class SubmissionManager {
    constructor(dataRoot, submissionsRoot, bucketSize = 100) {
        this.dataRoot = dataRoot;
        this.submissionsRoot = submissionsRoot;
        this.bucketSize = bucketSize;
        this.sid = null;
    }

    async init() {
        this.sid = await this.getStartSid();
        return this;
    }

    submissionPaths(sid) {
        const bucketPrefix = Math.floor(sid / this.bucketSize) * this.bucketSize;
        const bucketDir = path.join(this.submissionsRoot, String(bucketPrefix));
        const subDir = path.join(bucketDir, String(sid));
        return { bucketDir, subDir };
    }

    async getStartSid() {
        await fs.mkdir(this.submissionsRoot, { recursive: true });
        const buckets = await fs.readdir(this.submissionsRoot, { withFileTypes: true }).catch(() => []);
        const numericBuckets = buckets
            .filter(d => d.isDirectory())
            .map(d => Number.parseInt(d.name, 10))
            .filter(Number.isFinite)
            .sort((a, b) => a - b);
        if (numericBuckets.length === 0) return 0;

        const lastBucket = numericBuckets.at(-1);
        const lastDir = path.join(this.submissionsRoot, String(lastBucket));
        const subs = await fs.readdir(lastDir, { withFileTypes: true }).catch(() => []);
        const sids = subs
            .filter(d => d.isDirectory())
            .map(d => Number.parseInt(d.name, 10))
            .filter(Number.isFinite);

        const maxSid = sids.length ? Math.max(...sids) : lastBucket - 1;
        return Math.max(0, maxSid);
    }

    async nextSubmissionId() {
        if (typeof this.sid !== 'number') {
            this.sid = await this.getStartSid();
        }
        for (; ;) {
            const trySid = this.sid + 1;
            const { bucketDir, subDir } = this.submissionPaths(trySid);
            await fs.mkdir(bucketDir, { recursive: true });
            try {
                await fs.mkdir(subDir, { recursive: false });
                this.sid = trySid;
                return trySid;
            } catch (e) {
                if (e && e.code === 'EEXIST') {
                    this.sid = trySid;
                    continue;
                }
                throw e;
            }
        }
    }

    async resetCounter() {
        this.sid = await this.getStartSid();
    }
}