#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int J, M;
    if (!(cin >> J >> M)) return 0;
    vector<vector<int>> route(J, vector<int>(M));
    vector<vector<long long>> proc(J, vector<long long>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m; long long p;
            cin >> m >> p;
            route[j][k] = m;
            proc[j][k] = p;
        }
    }
    
    vector<int> nextOpIdx(J, 0);
    vector<long long> jobReady(J, 0), machReady(M, 0);
    vector<vector<int>> machineOrder(M);
    machineOrder.assign(M, vector<int>());
    machineOrder.reserve(M);
    long long remaining = 1LL * J * M;
    
    while (remaining > 0) {
        int bestJob = -1;
        int bestMachine = -1;
        long long bestEST = 0, bestEFT = 0, bestP = 0;
        for (int j = 0; j < J; ++j) {
            int k = nextOpIdx[j];
            if (k >= M) continue;
            int m = route[j][k];
            long long p = proc[j][k];
            long long est = max(jobReady[j], machReady[m]);
            long long eft = est + p;
            if (bestJob == -1 ||
                eft < bestEFT ||
                (eft == bestEFT && (est < bestEST ||
                 (est == bestEST && (p < bestP || (p == bestP && j < bestJob)))))) {
                bestJob = j;
                bestMachine = m;
                bestEST = est;
                bestEFT = eft;
                bestP = p;
            }
        }
        // Schedule bestJob on bestMachine
        machineOrder[bestMachine].push_back(bestJob);
        jobReady[bestJob] = bestEFT;
        machReady[bestMachine] = bestEFT;
        nextOpIdx[bestJob]++;
        remaining--;
    }
    
    // Output machine orders
    for (int m = 0; m < M; ++m) {
        // Ensure permutation length J; if not, fill remaining jobs (shouldn't happen)
        if ((int)machineOrder[m].size() != J) {
            vector<int> seen(J, 0);
            for (int x : machineOrder[m]) if (0 <= x && x < J) seen[x] = 1;
            for (int j = 0; j < J; ++j) if (!seen[j]) machineOrder[m].push_back(j);
        }
        for (int i = 0; i < J; ++i) {
            if (i) cout << ' ';
            cout << machineOrder[m][i];
        }
        cout << '\n';
    }
    return 0;
}