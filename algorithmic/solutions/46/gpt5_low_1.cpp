#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int J, M;
    if(!(cin >> J >> M)) return 0;
    vector<vector<int>> route(J, vector<int>(M));
    vector<vector<long long>> proc(J, vector<long long>(M));
    vector<vector<int>> posInJob(J, vector<int>(M, -1));
    for(int j=0;j<J;j++){
        for(int k=0;k<M;k++){
            int m; long long p;
            cin >> m >> p;
            route[j][k] = m;
            proc[j][k] = p;
        }
    }
    // Build position lookup: for job j, for machine m, what's the operation index k
    for(int j=0;j<J;j++){
        for(int k=0;k<M;k++){
            int m = route[j][k];
            posInJob[j][m] = k;
        }
    }

    // Giffler-Thompson heuristic to produce machine orders
    vector<long long> jobReady(J, 0), machReady(M, 0);
    vector<int> nextOpIdx(J, 0);
    vector<vector<int>> machineOrder(M);
    machineOrder.assign(M, vector<int>());
    machineOrder.reserve(M);
    int remaining = J * M;

    // For efficiency, maintain a list of candidate operations: next for each job
    while(remaining > 0){
        // Compute ES and EC for each job's next operation (if exists)
        long long bestEC = LLONG_MAX;
        int bestJob = -1;
        int bestMachine = -1;
        long long bestES = 0;
        for(int j=0;j<J;j++){
            int k = nextOpIdx[j];
            if(k >= M) continue;
            int m = route[j][k];
            long long p = proc[j][k];
            long long ES = max(jobReady[j], machReady[m]);
            long long EC = ES + p;
            if(EC < bestEC || (EC == bestEC && (p < proc[bestJob][nextOpIdx[bestJob]]))) {
                bestEC = EC;
                bestJob = j;
                bestMachine = m;
                bestES = ES;
            }
        }
        if(bestJob == -1){
            // Should not happen, but break to avoid infinite loop
            break;
        }
        // Build conflicting set on bestMachine: ops requiring m* with ES < bestEC
        int mstar = bestMachine;
        vector<int> conflictJobs;
        conflictJobs.reserve(J);
        for(int j=0;j<J;j++){
            int k = nextOpIdx[j];
            if(k >= M) continue;
            if(route[j][k] != mstar) continue;
            long long ES = max(jobReady[j], machReady[mstar]);
            if(ES < bestEC) conflictJobs.push_back(j);
        }
        // Choose one from conflict set by priority rule:
        // Shortest processing time (SPT), tie-breaker earlier ES, then smaller job id.
        int chosenJob = -1;
        long long bestP = LLONG_MAX;
        long long tieES = 0;
        for(int j: conflictJobs){
            int k = nextOpIdx[j];
            long long p = proc[j][k];
            long long ES = max(jobReady[j], machReady[mstar]);
            if(p < bestP || (p == bestP && (ES < tieES || (ES == tieES && j < chosenJob)))) {
                bestP = p;
                tieES = ES;
                chosenJob = j;
            }
        }
        if(chosenJob == -1) chosenJob = bestJob;
        int k = nextOpIdx[chosenJob];
        long long start = max(jobReady[chosenJob], machReady[mstar]);
        long long finish = start + proc[chosenJob][k];
        // Record order on machine
        machineOrder[mstar].push_back(chosenJob);
        // Update times and indices
        jobReady[chosenJob] = finish;
        machReady[mstar] = finish;
        nextOpIdx[chosenJob]++;
        remaining--;
    }

    // Ensure each machine has exactly J jobs; if not (due to any anomaly), fill missing with any not yet used
    for(int m=0;m<M;m++){
        if((int)machineOrder[m].size() < J){
            vector<int> used(J,0);
            for(int x: machineOrder[m]) if(0<=x && x<J) used[x]=1;
            for(int j=0;j<J;j++){
                if(!used[j]) machineOrder[m].push_back(j);
            }
        }
        // If more than J (shouldn't happen), trim
        if((int)machineOrder[m].size() > J){
            machineOrder[m].resize(J);
        }
    }

    // Output machine orders
    for(int m=0;m<M;m++){
        for(int idx=0; idx<J; idx++){
            if(idx) cout << ' ';
            cout << machineOrder[m][idx];
        }
        cout << "\n";
    }
    return 0;
}