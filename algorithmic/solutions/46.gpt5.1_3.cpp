#include <bits/stdc++.h>
using namespace std;

const int MAXJ = 60;
const int MAXM = 30;
const int MAXV = MAXJ * MAXM;
const long long INF = (1LL << 62);

int J, M;
int machineOfJobOp[MAXJ][MAXM];
int procTimeOfJobOp[MAXJ][MAXM];
int stepOfMachine[MAXJ][MAXM];
long long suffixProcTime[MAXJ][MAXM + 1];
long long opProcTime[MAXV];

vector<int> adj[MAXV];
int indegArr[MAXV];
long long distArr[MAXV];
int topoQueue[MAXV];

mt19937_64 rng(123456789);

long long compute_makespan(const vector<vector<int>>& machineOrder) {
    int V = J * M;

    for (int v = 0; v < V; ++v) {
        adj[v].clear();
        indegArr[v] = 0;
        distArr[v] = 0;
    }

    // Job precedence edges
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M - 1; ++k) {
            int u = j * M + k;
            int v = u + 1;
            adj[u].push_back(v);
            indegArr[v]++;
        }
    }

    // Machine precedence edges
    for (int m = 0; m < M; ++m) {
        const auto& seq = machineOrder[m];
        int sz = (int)seq.size();
        for (int pos = 1; pos < sz; ++pos) {
            int jobPrev = seq[pos - 1];
            int jobCur  = seq[pos];
            int stepPrev = stepOfMachine[jobPrev][m];
            int stepCur  = stepOfMachine[jobCur][m];
            int u = jobPrev * M + stepPrev;
            int v = jobCur  * M + stepCur;
            adj[u].push_back(v);
            indegArr[v]++;
        }
    }

    int qh = 0, qt = 0;
    int Vlimit = J * M;
    for (int v = 0; v < Vlimit; ++v) {
        if (indegArr[v] == 0) {
            topoQueue[qt++] = v;
        }
    }

    int processed = 0;
    long long Cmax = 0;

    while (qh < qt) {
        int v = topoQueue[qh++];
        processed++;

        long long comp = distArr[v] + opProcTime[v];
        if (comp > Cmax) Cmax = comp;

        for (int w : adj[v]) {
            if (distArr[w] < comp) distArr[w] = comp;
            if (--indegArr[w] == 0) {
                topoQueue[qt++] = w;
            }
        }
    }

    if (processed < Vlimit) return INF;
    return Cmax;
}

void build_schedule(int heurId, vector<vector<int>>& machineOrder, long long &makespan) {
    machineOrder.assign(M, vector<int>());
    for (int m = 0; m < M; ++m) {
        machineOrder[m].reserve(J);
    }

    vector<int> jobNextOp(J, 0);
    vector<long long> jobReady(J, 0);
    vector<long long> machineFree(M, 0);

    long long Cmax = 0;
    int totalOps = J * M;
    int scheduledOps = 0;

    while (scheduledOps < totalOps) {
        int bestJob = -1;
        long long bestPrimary = 0;
        long long bestTie = 0;

        for (int j = 0; j < J; ++j) {
            int s = jobNextOp[j];
            if (s >= M) continue;

            int m = machineOfJobOp[j][s];
            long long pt = procTimeOfJobOp[j][s];
            long long est = jobReady[j];
            if (machineFree[m] > est) est = machineFree[m];
            long long rem = suffixProcTime[j][s];

            long long primary, tie;
            switch (heurId) {
                case 0:
                    primary = est;
                    tie = j;
                    break;
                case 1:
                    primary = est + pt;
                    tie = j;
                    break;
                case 2:
                    primary = est;
                    tie = -rem;
                    break;
                case 3:
                    primary = est;
                    tie = -pt;
                    break;
                case 4:
                    primary = est;
                    tie = rem;
                    break;
                case 5:
                    primary = est;
                    tie = pt;
                    break;
                case 6:
                    primary = est + rem;
                    tie = j;
                    break;
                case 7:
                    primary = est + 2 * pt;
                    tie = j;
                    break;
                case 8:
                    primary = est;
                    tie = -j;
                    break;
                case 9:
                    primary = est;
                    tie = (long long)rng();
                    break;
                case 10:
                    primary = est + pt;
                    tie = -rem;
                    break;
                case 11:
                    primary = est + rem;
                    tie = -pt;
                    break;
                default:
                    primary = est;
                    tie = j;
                    break;
            }

            if (bestJob == -1 ||
                primary < bestPrimary ||
                (primary == bestPrimary && (tie < bestTie || (tie == bestTie && j < bestJob)))) {
                bestJob = j;
                bestPrimary = primary;
                bestTie = tie;
            }
        }

        int j = bestJob;
        int s = jobNextOp[j];
        int m = machineOfJobOp[j][s];
        long long pt = procTimeOfJobOp[j][s];
        long long est = jobReady[j];
        if (machineFree[m] > est) est = machineFree[m];

        long long startTime = est;
        long long finishTime = startTime + pt;

        jobReady[j] = finishTime;
        machineFree[m] = finishTime;
        jobNextOp[j]++;

        machineOrder[m].push_back(j);

        if (finishTime > Cmax) Cmax = finishTime;
        scheduledOps++;
    }

    makespan = Cmax;
}

int neighborEvaluations = 0;
const int MAX_NEIGHBOR_EVAL = 20000;

void local_search(vector<vector<int>>& order, long long &bestMakespan) {
    bool improved = true;
    while (improved) {
        improved = false;
        for (int m = 0; m < M; ++m) {
            auto &seq = order[m];
            for (int pos = 0; pos + 1 < J; ++pos) {
                if (neighborEvaluations >= MAX_NEIGHBOR_EVAL) return;

                swap(seq[pos], seq[pos + 1]);
                long long ms = compute_makespan(order);
                neighborEvaluations++;

                if (ms < bestMakespan && ms < INF) {
                    bestMakespan = ms;
                    improved = true;
                } else {
                    swap(seq[pos], seq[pos + 1]);
                }
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> J >> M)) {
        return 0;
    }

    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m;
            int p;
            cin >> m >> p;
            machineOfJobOp[j][k] = m;
            procTimeOfJobOp[j][k] = p;
            stepOfMachine[j][m] = k;
        }
    }

    for (int j = 0; j < J; ++j) {
        suffixProcTime[j][M] = 0;
        for (int k = M - 1; k >= 0; --k) {
            suffixProcTime[j][k] = suffixProcTime[j][k + 1] + (long long)procTimeOfJobOp[j][k];
            int id = j * M + k;
            opProcTime[id] = (long long)procTimeOfJobOp[j][k];
        }
    }

    const int HEUR_COUNT = 12;
    vector<vector<int>> bestOrder(M);
    long long bestMakespan = INF;

    for (int h = 0; h < HEUR_COUNT; ++h) {
        vector<vector<int>> candOrder(M);
        long long candMakespan;
        build_schedule(h, candOrder, candMakespan);
        if (candMakespan < bestMakespan) {
            bestMakespan = candMakespan;
            bestOrder = candOrder;
        }
    }

    // Optional local search refinement
    local_search(bestOrder, bestMakespan);

    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J; ++i) {
            if (i) cout << ' ';
            cout << bestOrder[m][i];
        }
        cout << '\n';
    }

    return 0;
}