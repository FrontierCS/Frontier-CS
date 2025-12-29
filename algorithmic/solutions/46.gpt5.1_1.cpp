#include <bits/stdc++.h>
using namespace std;

int J, M;
vector<vector<int>> jobMachine;
vector<vector<long long>> jobProc;
vector<long long> jobTotalTime;
mt19937_64 rng;

struct Schedule {
    long long makespan;
    vector<vector<int>> order;
};

Schedule runHeuristic(int heurId) {
    vector<long long> jobReady(J, 0), machReady(M, 0);
    vector<long long> jobRemaining = jobTotalTime;
    vector<int> jobNext(J, 0);

    vector<vector<int>> order(M);
    for (int m = 0; m < M; ++m) order[m].reserve(J);

    long long globalMakespan = 0;
    int steps = J * M;

    for (int step = 0; step < steps; ++step) {
        int chosenJob = -1;
        double bestScore = 0.0;
        long long chosenStart = 0;

        for (int j = 0; j < J; ++j) {
            if (jobNext[j] >= M) continue;
            int k = jobNext[j];
            int m = jobMachine[j][k];
            long long p = jobProc[j][k];
            long long e = jobReady[j] > machReady[m] ? jobReady[j] : machReady[m];
            long long c = e + p;
            long long rem = jobRemaining[j];

            double score;
            switch (heurId) {
                case 0: // Earliest completion time
                    score = (double)c;
                    break;
                case 1: // Shortest processing time (SPT)
                    score = (double)p + 1e-6 * (double)e;
                    break;
                case 2: // Longest processing time (LPT)
                    score = -(double)p + 1e-6 * (double)e;
                    break;
                case 3: // MWKR + ECT
                    score = (double)c - 0.1 * (double)rem;
                    break;
                case 4: // MWKR + EST
                    score = (double)e - 0.1 * (double)rem;
                    break;
                case 5: // Prefer jobs near completion
                    score = (double)c + 0.1 * (double)rem;
                    break;
                case 6: // Earliest start time
                    score = (double)e;
                    break;
                case 7: // Random
                    score = (double)(rng() & 0xFFFFFFFFULL);
                    break;
                default:
                    score = (double)c;
                    break;
            }

            if (chosenJob == -1 || score < bestScore) {
                chosenJob = j;
                bestScore = score;
                chosenStart = e;
            }
        }

        int j = chosenJob;
        int k = jobNext[j];
        int m = jobMachine[j][k];
        long long p = jobProc[j][k];
        long long start = chosenStart;
        long long finish = start + p;

        jobReady[j] = finish;
        machReady[m] = finish;
        jobNext[j]++;
        jobRemaining[j] -= p;
        order[m].push_back(j);
        if (finish > globalMakespan) globalMakespan = finish;
    }

    Schedule res;
    res.makespan = globalMakespan;
    res.order = std::move(order);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> J >> M)) return 0;

    jobMachine.assign(J, vector<int>(M));
    jobProc.assign(J, vector<long long>(M));
    jobTotalTime.assign(J, 0);

    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m;
            long long p;
            cin >> m >> p;
            jobMachine[j][k] = m;
            jobProc[j][k] = p;
            jobTotalTime[j] += p;
        }
    }

    uint64_t seed = 712367821ull;
    seed ^= (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    rng.seed(seed);

    const int HEUR_COUNT = 8;
    const int MAX_RUNS = 200;
    const double TIME_LIMIT = 0.9; // seconds

    auto startClock = chrono::high_resolution_clock::now();

    Schedule best;
    best.makespan = numeric_limits<long long>::max();

    for (int run = 0; run < MAX_RUNS; ++run) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - startClock).count();
        if (run > 0 && elapsed > TIME_LIMIT) break;

        int heurId;
        if (run < HEUR_COUNT) heurId = run;
        else heurId = (int)(rng() % HEUR_COUNT);

        Schedule cur = runHeuristic(heurId);
        if (cur.makespan < best.makespan) {
            best = std::move(cur);
        }
    }

    for (int m = 0; m < M; ++m) {
        if (m < (int)best.order.size() && (int)best.order[m].size() == J) {
            for (int i = 0; i < J; ++i) {
                if (i) cout << ' ';
                cout << best.order[m][i];
            }
        } else {
            // Fallback: simple permutation if something went wrong
            for (int j = 0; j < J; ++j) {
                if (j) cout << ' ';
                cout << j;
            }
        }
        cout << '\n';
    }

    return 0;
}