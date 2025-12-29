#include <bits/stdc++.h>
using namespace std;

struct Operation {
    int machine;
    long long p;
};

long long evaluatePerm(const vector<int>& perm, const vector<vector<Operation>>& jobs, int M) {
    vector<long long> machineReady(M, 0);
    long long makespan = 0;
    for (int jobId : perm) {
        const auto& ops = jobs[jobId];
        long long t = 0;
        for (const auto& op : ops) {
            long long s = t;
            if (machineReady[op.machine] > s) s = machineReady[op.machine];
            t = s + op.p;
            machineReady[op.machine] = t;
        }
        if (t > makespan) makespan = t;
    }
    return makespan;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int J, M;
    if (!(cin >> J >> M)) return 0;

    vector<vector<Operation>> jobs(J, vector<Operation>(M));
    vector<long long> jobTotal(J, 0);

    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m;
            long long p;
            cin >> m >> p;
            jobs[j][k] = {m, p};
            jobTotal[j] += p;
        }
    }

    // NEH-like construction of a global job order (same for all machines)
    vector<int> order(J);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (jobTotal[a] != jobTotal[b]) return jobTotal[a] > jobTotal[b];
        return a < b;
    });

    vector<int> perm;
    perm.reserve(J);

    // Build permutation incrementally
    for (int idx = 0; idx < J; ++idx) {
        int job = order[idx];
        if (perm.empty()) {
            perm.push_back(job);
            continue;
        }
        long long bestMS = (1LL<<62);
        vector<int> bestPerm;
        bestPerm.reserve(perm.size() + 1);
        for (int pos = 0; pos <= (int)perm.size(); ++pos) {
            vector<int> cand;
            cand.reserve(perm.size() + 1);
            for (int i = 0; i < pos; ++i) cand.push_back(perm[i]);
            cand.push_back(job);
            for (int i = pos; i < (int)perm.size(); ++i) cand.push_back(perm[i]);
            long long ms = evaluatePerm(cand, jobs, M);
            if (ms < bestMS) {
                bestMS = ms;
                bestPerm.swap(cand);
            }
        }
        perm.swap(bestPerm);
    }

    // Local search: pairwise swaps
    long long bestMS = evaluatePerm(perm, jobs, M);
    const int maxPasses = 3;
    for (int pass = 0; pass < maxPasses; ++pass) {
        bool improved = false;
        for (int i = 0; i < J; ++i) {
            for (int j = i + 1; j < J; ++j) {
                swap(perm[i], perm[j]);
                long long ms = evaluatePerm(perm, jobs, M);
                if (ms < bestMS) {
                    bestMS = ms;
                    improved = true;
                } else {
                    swap(perm[i], perm[j]); // revert
                }
            }
        }
        if (!improved) break;
    }

    // Output the same permutation for all machines
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J; ++i) {
            if (i) cout << ' ';
            cout << perm[i];
        }
        cout << '\n';
    }

    return 0;
}