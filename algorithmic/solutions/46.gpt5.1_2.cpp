#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int J, M;
    if (!(cin >> J >> M)) return 0;

    vector<vector<int>> jobMachine(J, vector<int>(M));
    vector<vector<long long>> jobProc(J, vector<long long>(M));

    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m;
            long long p;
            cin >> m >> p;
            jobMachine[j][k] = m;
            jobProc[j][k] = p;
        }
    }

    // jobPos[j][m] = position k in job j where machine m is processed
    vector<vector<int>> jobPos(J, vector<int>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m = jobMachine[j][k];
            jobPos[j][m] = k;
        }
    }

    // Suffix sums of remaining work per job
    vector<vector<long long>> suffix(J, vector<long long>(M + 1, 0));
    for (int j = 0; j < J; ++j) {
        suffix[j][M] = 0;
        for (int k = M - 1; k >= 0; --k) {
            suffix[j][k] = suffix[j][k + 1] + jobProc[j][k];
        }
    }

    int Nops = J * M;
    vector<long long> bestStart(Nops, 0), tmpStart(Nops, 0), tmpEnd(Nops, 0);
    long long bestCmax = (1LL << 62);

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> dist01(0.0, 1.0);

    auto startTime = chrono::steady_clock::now();

    int totalOps = Nops;
    int maxIter;
    if (totalOps <= 200) maxIter = 1200;
    else if (totalOps <= 500) maxIter = 800;
    else if (totalOps <= 800) maxIter = 600;
    else maxIter = 450;

    auto scheduleRun = [&](double w_rem, double w_p, double w_ops, double w_rand) {
        vector<int> jobPtr(J, 0);
        vector<long long> jobReady(J, 0), machReady(M, 0);
        vector<int> cand;
        cand.reserve(J);

        for (int step = 0; step < Nops; ++step) {
            long long bestR = (long long)4e18;
            cand.clear();

            for (int j = 0; j < J; ++j) {
                int k = jobPtr[j];
                if (k >= M) continue;
                int mach = jobMachine[j][k];
                long long r = jobReady[j] > machReady[mach] ? jobReady[j] : machReady[mach];
                if (r < bestR) {
                    bestR = r;
                    cand.clear();
                    cand.push_back(j);
                } else if (r == bestR) {
                    cand.push_back(j);
                }
            }

            int chosenJ = cand[0];
            double bestScore = -1e100;

            for (int idxCand = 0; idxCand < (int)cand.size(); ++idxCand) {
                int j = cand[idxCand];
                int k = jobPtr[j];
                long long p = jobProc[j][k];
                long long remWork = suffix[j][k];
                int opsRem = M - k;

                double score = w_rem * (double)remWork + w_p * (double)p + w_ops * (double)opsRem;
                if (w_rand != 0.0) {
                    score += w_rand * dist01(rng);
                }

                if (score > bestScore) {
                    bestScore = score;
                    chosenJ = j;
                }
            }

            int j = chosenJ;
            int k = jobPtr[j];
            int mach = jobMachine[j][k];
            long long p = jobProc[j][k];

            long long s = jobReady[j] > machReady[mach] ? jobReady[j] : machReady[mach];
            long long e = s + p;

            int opIndex = j * M + k;
            tmpStart[opIndex] = s;
            tmpEnd[opIndex] = e;

            jobReady[j] = e;
            machReady[mach] = e;
            jobPtr[j]++;
        }

        long long Cmax = 0;
        for (int j = 0; j < J; ++j) {
            if (jobReady[j] > Cmax) Cmax = jobReady[j];
        }

        if (Cmax < bestCmax) {
            bestCmax = Cmax;
            bestStart = tmpStart;
        }
    };

    // Deterministic base heuristics
    scheduleRun(1.0, 0.0, 0.0, 0.0);   // MWKR
    scheduleRun(0.0, 1.0, 0.0, 0.0);   // LPT
    scheduleRun(0.0, -1.0, 0.0, 0.0);  // SPT
    scheduleRun(0.0, 0.0, 1.0, 0.0);   // OPN

    int baseRuns = 4;

    for (int iter = baseRuns; iter < maxIter; ++iter) {
        if (iter % 10 == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - startTime).count();
            if (elapsed > 1.8) break;
        }

        double a, b, c, w_rand;
        int ruleType = uniform_int_distribution<int>(0, 4)(rng); // 0..3 deterministic, 4 mixed

        if (ruleType == 0) { // MWKR
            a = 1.0; b = 0.0; c = 0.0; w_rand = 0.0;
        } else if (ruleType == 1) { // LPT
            a = 0.0; b = 1.0; c = 0.0; w_rand = 0.0;
        } else if (ruleType == 2) { // SPT
            a = 0.0; b = -1.0; c = 0.0; w_rand = 0.0;
        } else if (ruleType == 3) { // OPN
            a = 0.0; b = 0.0; c = 1.0; w_rand = 0.0;
        } else { // Mixed heuristic
            uniform_real_distribution<double> distA(0.0, 1.0);
            uniform_real_distribution<double> distB(-1.0, 1.0);
            a = distA(rng);      // weight for remaining work (>=0)
            b = distB(rng);      // weight for p (can be +/-)
            c = distA(rng);      // weight for ops remaining (>=0)
            w_rand = 0.1;        // random noise
        }

        scheduleRun(a, b, c, w_rand);
    }

    // Build permutations per machine from bestStart times
    for (int m = 0; m < M; ++m) {
        vector<pair<long long, int>> arr;
        arr.reserve(J);
        for (int j = 0; j < J; ++j) {
            int k = jobPos[j][m];
            int idx = j * M + k;
            long long s = bestStart[idx];
            arr.emplace_back(s, j);
        }
        sort(arr.begin(), arr.end());
        for (int i = 0; i < J; ++i) {
            if (i) cout << ' ';
            cout << arr[i].second;
        }
        cout << '\n';
    }

    return 0;
}