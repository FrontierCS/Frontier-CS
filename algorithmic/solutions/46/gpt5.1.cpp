#include <bits/stdc++.h>
using namespace std;

int J, M;
vector<vector<int>> jobMachine;
vector<vector<long long>> jobProc;
vector<vector<long long>> jobSuffix;

struct Schedule {
    long long makespan;
    vector<vector<int>> machineSeq;
};

mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

Schedule build_schedule(int ruleType, long long w_s = 0, long long w_r = 0, long long w_p = 0) {
    vector<int> nextOp(J, 0);
    vector<long long> jobEnd(J, 0), machineEnd(M, 0);
    vector<vector<int>> machineSeq(M);
    for (int m = 0; m < M; ++m) machineSeq[m].reserve(J);

    int remainingOps = J * M;

    while (remainingOps > 0) {
        int bestJob = -1;
        long long best1 = 0, best2 = 0, best3 = 0;

        for (int j = 0; j < J; ++j) {
            int k = nextOp[j];
            if (k >= M) continue;

            int m = jobMachine[j][k];
            long long p = jobProc[j][k];
            long long s = jobEnd[j] >= machineEnd[m] ? jobEnd[j] : machineEnd[m];
            long long f = s + p;
            long long rem = jobSuffix[j][k]; // remaining work including this op

            switch (ruleType) {
                case 0: { // Earliest Finish Time (EFT)
                    if (bestJob == -1 ||
                        f < best1 ||
                        (f == best1 && rem > best2) ||
                        (f == best1 && rem == best2 && j < bestJob)) {
                        bestJob = j;
                        best1 = f;
                        best2 = rem;
                    }
                    break;
                }
                case 1: { // Earliest Start, then Shortest Processing Time
                    if (bestJob == -1 ||
                        s < best1 ||
                        (s == best1 && p < best2) ||
                        (s == best1 && p == best2 && rem > best3) ||
                        (s == best1 && p == best2 && rem == best3 && j < bestJob)) {
                        bestJob = j;
                        best1 = s;
                        best2 = p;
                        best3 = rem;
                    }
                    break;
                }
                case 2: { // Most Work Remaining (MWKR)
                    if (bestJob == -1 ||
                        rem > best1 ||
                        (rem == best1 && s < best2) ||
                        (rem == best1 && s == best2 && p < best3) ||
                        (rem == best1 && s == best2 && p == best3 && j < bestJob)) {
                        bestJob = j;
                        best1 = rem;
                        best2 = s;
                        best3 = p;
                    }
                    break;
                }
                case 3: { // Weighted combination of s, rem, p
                    long long pri = w_s * s + w_r * rem + w_p * p;
                    if (bestJob == -1 ||
                        pri < best1 ||
                        (pri == best1 && s < best2) ||
                        (pri == best1 && s == best2 && p < best3) ||
                        (pri == best1 && s == best2 && p == best3 && j < bestJob)) {
                        bestJob = j;
                        best1 = pri;
                        best2 = s;
                        best3 = p;
                    }
                    break;
                }
            }
        }

        int k = nextOp[bestJob];
        int m = jobMachine[bestJob][k];
        long long p = jobProc[bestJob][k];
        long long s = jobEnd[bestJob] >= machineEnd[m] ? jobEnd[bestJob] : machineEnd[m];
        long long c = s + p;

        jobEnd[bestJob] = c;
        machineEnd[m] = c;
        machineSeq[m].push_back(bestJob);
        nextOp[bestJob]++;
        remainingOps--;
    }

    long long makespan = 0;
    for (int j = 0; j < J; ++j) if (jobEnd[j] > makespan) makespan = jobEnd[j];

    Schedule res;
    res.makespan = makespan;
    res.machineSeq = std::move(machineSeq);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> J >> M)) return 0;

    jobMachine.assign(J, vector<int>(M));
    jobProc.assign(J, vector<long long>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m;
            long long p;
            cin >> m >> p;
            jobMachine[j][k] = m;
            jobProc[j][k] = p;
        }
    }

    jobSuffix.assign(J, vector<long long>(M + 1));
    for (int j = 0; j < J; ++j) {
        jobSuffix[j][M] = 0;
        for (int k = M - 1; k >= 0; --k) {
            jobSuffix[j][k] = jobSuffix[j][k + 1] + jobProc[j][k];
        }
    }

    auto startTime = chrono::steady_clock::now();
    const double TIME_LIMIT = 0.95; // seconds

    Schedule best;
    bool haveBest = false;

    struct Param { int rule; long long ws, wr, wp; };
    vector<Param> initialParams;
    initialParams.push_back({0, 0, 0, 0});          // EFT
    initialParams.push_back({1, 0, 0, 0});          // EST+SPT
    initialParams.push_back({2, 0, 0, 0});          // MWKR
    initialParams.push_back({3, 1, -1, 1});         // one fixed weighted combo

    for (const auto &par : initialParams) {
        Schedule s = build_schedule(par.rule, par.ws, par.wr, par.wp);
        if (!haveBest || s.makespan < best.makespan) {
            best = std::move(s);
            haveBest = true;
        }
    }

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - startTime).count();
        if (elapsed > TIME_LIMIT) break;

        int ruleType;
        long long ws = 0, wr = 0, wp = 0;

        uint64_t r = rng();
        int sel = r & 3;
        if (sel == 0) ruleType = 0;
        else if (sel == 1) ruleType = 1;
        else if (sel == 2) ruleType = 2;
        else {
            ruleType = 3;
            ws = (long long)(rng() % 5);          // 0..4
            wp = (long long)(rng() % 3);          // 0..2
            wr = (long long)((int)(rng() % 7) - 3); // -3..3
            if (ws == 0 && wp == 0 && wr == 0) ws = 1;
        }

        Schedule s = build_schedule(ruleType, ws, wr, wp);
        if (s.makespan < best.makespan) {
            best = std::move(s);
        }
    }

    // Output machine sequences
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < (int)best.machineSeq[m].size(); ++i) {
            if (i) cout << ' ';
            cout << best.machineSeq[m][i];
        }
        cout << '\n';
    }

    return 0;
}