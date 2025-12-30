#include <bits/stdc++.h>
using namespace std;

struct JSSPSolver {
    int J, M, N;

    vector<vector<int>> mach;          // mach[j][k] = machine index of k-th op in job j
    vector<vector<long long>> pt;      // pt[j][k]   = processing time
    vector<vector<int>> posInJob;      // posInJob[j][m] = position k where job j uses machine m
    vector<vector<int>> opIdJM;        // opIdJM[j][m] = opId of job j on machine m

    vector<long long> dur;             // dur[opId]
    vector<int> jobPred, jobSucc;      // fixed arcs along jobs

    // Reusable buffers for evaluation
    vector<int> machPred, machSucc;
    vector<int> indeg;
    vector<long long> comp;
    vector<int> q;

    static constexpr long long INF = (1LL << 62);

    JSSPSolver(int J_, int M_) : J(J_), M(M_), N(J_ * M_) {
        mach.assign(J, vector<int>(M, 0));
        pt.assign(J, vector<long long>(M, 0));
        posInJob.assign(J, vector<int>(M, -1));
        opIdJM.assign(J, vector<int>(M, -1));

        dur.assign(N, 0);
        jobPred.assign(N, -1);
        jobSucc.assign(N, -1);

        machPred.assign(N, -1);
        machSucc.assign(N, -1);
        indeg.assign(N, 0);
        comp.assign(N, 0);
        q.reserve(N);
    }

    inline int opId(int j, int k) const { return j * M + k; }

    long long evaluate(const vector<vector<int>>& ord) {
        fill(machPred.begin(), machPred.end(), -1);
        fill(machSucc.begin(), machSucc.end(), -1);

        for (int m = 0; m < M; m++) {
            int prevOp = -1;
            for (int idx = 0; idx < J; idx++) {
                int job = ord[m][idx];
                int op = opIdJM[job][m];
                if (op < 0) return INF;
                if (prevOp != -1) {
                    machPred[op] = prevOp;
                    machSucc[prevOp] = op;
                }
                prevOp = op;
            }
        }

        for (int i = 0; i < N; i++) {
            indeg[i] = (jobPred[i] != -1) + (machPred[i] != -1);
            comp[i] = 0;
        }

        q.clear();
        for (int i = 0; i < N; i++) if (indeg[i] == 0) q.push_back(i);

        int head = 0, processed = 0;
        long long makespan = 0;

        while (head < (int)q.size()) {
            int u = q[head++];
            processed++;

            long long start = 0;
            int p1 = jobPred[u];
            if (p1 != -1) start = max(start, comp[p1]);
            int p2 = machPred[u];
            if (p2 != -1) start = max(start, comp[p2]);

            comp[u] = start + dur[u];
            makespan = max(makespan, comp[u]);

            int v1 = jobSucc[u];
            if (v1 != -1) {
                if (--indeg[v1] == 0) q.push_back(v1);
            }
            int v2 = machSucc[u];
            if (v2 != -1) {
                if (--indeg[v2] == 0) q.push_back(v2);
            }
        }

        if (processed != N) return INF;
        return makespan;
    }

    vector<vector<int>> buildOrder(int mode, mt19937& rng) {
        vector<vector<int>> ord(M);
        for (int m = 0; m < M; m++) ord[m].reserve(J);

        vector<int> idx(J, 0);
        vector<long long> jobReady(J, 0), machReady(M, 0), remWork(J, 0);

        for (int j = 0; j < J; j++) {
            long long sum = 0;
            for (int k = 0; k < M; k++) sum += pt[j][k];
            remWork[j] = sum;
        }

        for (int step = 0; step < N; step++) {
            int bestJob = -1;
            long long bestK1 = 0, bestK2 = 0, bestK3 = 0;
            uint32_t bestRnd = 0;

            for (int j = 0; j < J; j++) {
                int k = idx[j];
                if (k >= M) continue;
                int m = mach[j][k];
                long long p = pt[j][k];
                long long est = max(jobReady[j], machReady[m]);

                long long k1 = est, k2 = 0, k3 = 0;
                switch (mode) {
                    case 0: // SPT tie-break
                        k2 = p; k3 = remWork[j];
                        break;
                    case 1: // Most work remaining first
                        k2 = -remWork[j]; k3 = p;
                        break;
                    case 2: // LPT tie-break
                        k2 = -p; k3 = -remWork[j];
                        break;
                    case 3: // Short remaining work (encourage finishing jobs)
                        k2 = remWork[j]; k3 = p;
                        break;
                    case 4: // Prefer ops that unlock large remaining (large remWork, small p)
                        k2 = -(remWork[j] * 1024LL - p); k3 = p;
                        break;
                    default:
                        k2 = p; k3 = remWork[j];
                        break;
                }
                uint32_t rnd = rng();

                if (bestJob == -1 ||
                    k1 < bestK1 ||
                    (k1 == bestK1 && (k2 < bestK2 ||
                    (k2 == bestK2 && (k3 < bestK3 ||
                    (k3 == bestK3 && rnd < bestRnd)))))) {
                    bestJob = j;
                    bestK1 = k1; bestK2 = k2; bestK3 = k3; bestRnd = rnd;
                }
            }

            int k = idx[bestJob];
            int m = mach[bestJob][k];
            long long p = pt[bestJob][k];
            long long est = max(jobReady[bestJob], machReady[m]);
            long long fin = est + p;

            ord[m].push_back(bestJob);

            jobReady[bestJob] = fin;
            machReady[m] = fin;
            remWork[bestJob] -= p;
            idx[bestJob]++;
        }

        return ord;
    }

    vector<vector<int>> solve() {
        mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ 0x9e3779b9U);

        vector<long long> machineLoad(M, 0);
        for (int j = 0; j < J; j++) for (int k = 0; k < M; k++) machineLoad[mach[j][k]] += pt[j][k];
        vector<long long> prefixLoad(M, 0);
        long long totalLoad = 0;
        for (int m = 0; m < M; m++) {
            totalLoad += max(1LL, machineLoad[m]);
            prefixLoad[m] = totalLoad;
        }

        auto pickMachine = [&]() -> int {
            if (M == 1) return 0;
            uniform_int_distribution<long long> dist(0, totalLoad - 1);
            long long r = dist(rng);
            int m = (int)(lower_bound(prefixLoad.begin(), prefixLoad.end(), r + 1) - prefixLoad.begin());
            if (m < 0) m = 0;
            if (m >= M) m = M - 1;
            return m;
        };

        auto startTime = chrono::high_resolution_clock::now();
        auto deadline = startTime + chrono::milliseconds(950);

        vector<vector<int>> bestOrd;
        long long bestVal = INF;

        // Construct multiple initial solutions
        int attempts = 0;
        for (int rep = 0; rep < 3; rep++) {
            for (int mode = 0; mode < 5; mode++) {
                if ((attempts & 7) == 0) {
                    if (chrono::high_resolution_clock::now() >= deadline) break;
                }
                attempts++;
                auto ord = buildOrder(mode, rng);
                long long val = evaluate(ord);
                if (val < bestVal) {
                    bestVal = val;
                    bestOrd = std::move(ord);
                }
            }
            if (chrono::high_resolution_clock::now() >= deadline) break;
        }

        if (bestOrd.empty()) {
            // Fallback: identity permutations (may be infeasible, but in trivial cases ok)
            bestOrd.assign(M, vector<int>(J));
            for (int m = 0; m < M; m++) iota(bestOrd[m].begin(), bestOrd[m].end(), 0);
            return bestOrd;
        }

        // Local search (simulated annealing)
        vector<vector<int>> curOrd = bestOrd;
        long long curVal = bestVal;

        uniform_real_distribution<double> u01(0.0, 1.0);

        double temp = max(1.0, (double)curVal * 0.05);
        const double alpha = 0.9995;

        int iter = 0;
        while (true) {
            if ((iter & 255) == 0) {
                if (chrono::high_resolution_clock::now() >= deadline) break;
            }
            iter++;

            int m = pickMachine();
            if (J <= 1) break;

            bool didMove = false;
            int moveType = (J >= 3 && u01(rng) < 0.20) ? 1 : 0; // 0=adjacent swap, 1=insert

            int i = 0, j = 0;
            if (moveType == 0) {
                uniform_int_distribution<int> di(0, J - 2);
                i = di(rng);
                swap(curOrd[m][i], curOrd[m][i + 1]);
                didMove = true;
            } else {
                uniform_int_distribution<int> dpos(0, J - 1);
                i = dpos(rng);
                j = dpos(rng);
                if (i == j) continue;
                if (i < j) {
                    rotate(curOrd[m].begin() + i, curOrd[m].begin() + i + 1, curOrd[m].begin() + j + 1);
                } else {
                    rotate(curOrd[m].begin() + j, curOrd[m].begin() + i, curOrd[m].begin() + i + 1);
                }
                didMove = true;
            }

            if (!didMove) continue;

            long long newVal = evaluate(curOrd);

            bool accept = false;
            if (newVal != INF) {
                long long delta = newVal - curVal;
                if (delta <= 0) {
                    accept = true;
                } else {
                    double prob = exp(-(double)delta / temp);
                    if (u01(rng) < prob) accept = true;
                }
            }

            if (accept) {
                curVal = newVal;
                if (curVal < bestVal) {
                    bestVal = curVal;
                    bestOrd = curOrd;
                }
            } else {
                // undo
                if (moveType == 0) {
                    swap(curOrd[m][i], curOrd[m][i + 1]);
                } else {
                    if (i < j) {
                        rotate(curOrd[m].begin() + i, curOrd[m].begin() + j, curOrd[m].begin() + j + 1);
                    } else {
                        rotate(curOrd[m].begin() + j, curOrd[m].begin() + j + 1, curOrd[m].begin() + i + 1);
                    }
                }
            }

            temp *= alpha;
            if (temp < 1e-6) temp = 1e-6;
        }

        return bestOrd;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int J, M;
    if (!(cin >> J >> M)) return 0;

    JSSPSolver solver(J, M);

    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            int m;
            long long p;
            cin >> m >> p;
            solver.mach[j][k] = m;
            solver.pt[j][k] = p;
        }
        for (int k = 0; k < M; k++) {
            int m = solver.mach[j][k];
            solver.posInJob[j][m] = k;
            solver.opIdJM[j][m] = solver.opId(j, k);
            int op = solver.opId(j, k);
            solver.dur[op] = solver.pt[j][k];
            solver.jobPred[op] = (k > 0) ? solver.opId(j, k - 1) : -1;
            solver.jobSucc[op] = (k + 1 < M) ? solver.opId(j, k + 1) : -1;
        }
    }

    auto bestOrd = solver.solve();

    for (int m = 0; m < M; m++) {
        for (int i = 0; i < J; i++) {
            if (i) cout << ' ';
            cout << bestOrd[m][i];
        }
        cout << "\n";
    }
    return 0;
}