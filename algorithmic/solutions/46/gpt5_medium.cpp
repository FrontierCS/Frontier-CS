#include <bits/stdc++.h>
using namespace std;

struct Op { int m; long long p; };

struct Result {
    long long makespan;
    vector<vector<int>> order;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int J, M;
    if (!(cin >> J >> M)) return 0;
    vector<vector<Op>> ops(J, vector<Op>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m; long long p;
            cin >> m >> p;
            ops[j][k] = {m, p};
        }
    }

    vector<long long> machineTotal(M, 0);
    vector<long long> jobTotal(J, 0);
    for (int j = 0; j < J; ++j) {
        long long sum = 0;
        for (int k = 0; k < M; ++k) {
            sum += ops[j][k].p;
            machineTotal[ops[j][k].m] += ops[j][k].p;
        }
        jobTotal[j] = sum;
    }

    auto run_heuristic = [&](int h)->Result {
        vector<int> nextIdx(J, 0);
        vector<long long> jobReady(J, 0), machReady(M, 0), rem = jobTotal;
        vector<vector<int>> order(M);
        for (int m = 0; m < M; ++m) order[m].reserve(J);
        long long makespan = 0;
        int N = J * M;
        for (int step = 0; step < N; ++step) {
            int best_j = -1;
            long long best_ec = 0, best_es = 0, best_rem = 0, best_load = 0;
            long long best_p = 0;
            for (int j = 0; j < J; ++j) {
                if (nextIdx[j] >= M) continue;
                int m = ops[j][nextIdx[j]].m;
                long long p = ops[j][nextIdx[j]].p;
                long long es = max(jobReady[j], machReady[m]);
                long long ec = es + p;
                long long rj = rem[j];
                long long load = machineTotal[m];

                bool better = false;
                if (best_j == -1) {
                    better = true;
                } else {
                    switch (h) {
                        case 0: { // ECT
                            if (ec < best_ec) better = true;
                            else if (ec == best_ec) {
                                if (es < best_es) better = true;
                                else if (es == best_es) {
                                    if (p < best_p) better = true;
                                    else if (p == best_p) {
                                        if (rj > best_rem) better = true;
                                        else if (rj == best_rem && j < best_j) better = true;
                                    }
                                }
                            }
                        } break;
                        case 1: { // EST
                            if (es < best_es) better = true;
                            else if (es == best_es) {
                                if (p < best_p) better = true;
                                else if (p == best_p) {
                                    if (rj > best_rem) better = true;
                                    else if (rj == best_rem) {
                                        if (ec < best_ec) better = true;
                                        else if (ec == best_ec && j < best_j) better = true;
                                    }
                                }
                            }
                        } break;
                        case 2: { // SPT
                            if (p < best_p) better = true;
                            else if (p == best_p) {
                                if (es < best_es) better = true;
                                else if (es == best_es) {
                                    if (ec < best_ec) better = true;
                                    else if (ec == best_ec) {
                                        if (rj > best_rem) better = true;
                                        else if (rj == best_rem && j < best_j) better = true;
                                    }
                                }
                            }
                        } break;
                        case 3: { // LPT
                            if (p > best_p) better = true;
                            else if (p == best_p) {
                                if (es < best_es) better = true;
                                else if (es == best_es) {
                                    if (ec < best_ec) better = true;
                                    else if (ec == best_ec) {
                                        if (rj > best_rem) better = true;
                                        else if (rj == best_rem && j < best_j) better = true;
                                    }
                                }
                            }
                        } break;
                        case 4: { // LRPT
                            if (rj > best_rem) better = true;
                            else if (rj == best_rem) {
                                if (es < best_es) better = true;
                                else if (es == best_es) {
                                    if (ec < best_ec) better = true;
                                    else if (ec == best_ec) {
                                        if (p < best_p) better = true;
                                        else if (p == best_p && j < best_j) better = true;
                                    }
                                }
                            }
                        } break;
                        case 5: { // Bottleneck-first then ECT
                            if (load > best_load) better = true;
                            else if (load == best_load) {
                                if (ec < best_ec) better = true;
                                else if (ec == best_ec) {
                                    if (es < best_es) better = true;
                                    else if (es == best_es) {
                                        if (p < best_p) better = true;
                                        else if (p == best_p) {
                                            if (rj > best_rem) better = true;
                                            else if (rj == best_rem && j < best_j) better = true;
                                        }
                                    }
                                }
                            }
                        } break;
                        default: break;
                    }
                }
                if (better) {
                    best_j = j;
                    best_ec = ec;
                    best_es = es;
                    best_p = p;
                    best_rem = rj;
                    best_load = load;
                }
            }
            int j = best_j;
            int k = nextIdx[j];
            int m = ops[j][k].m;
            long long p = ops[j][k].p;
            long long s = max(jobReady[j], machReady[m]);
            long long f = s + p;
            jobReady[j] = f;
            machReady[m] = f;
            nextIdx[j] = k + 1;
            rem[j] -= p;
            order[m].push_back(j);
            if (f > makespan) makespan = f;
        }
        return {makespan, order};
    };

    vector<int> heuristics = {0,1,2,3,4,5};
    long long bestP = LLONG_MAX;
    vector<vector<int>> bestOrder;
    for (int h : heuristics) {
        Result r = run_heuristic(h);
        if (r.makespan < bestP) {
            bestP = r.makespan;
            bestOrder = move(r.order);
        }
    }

    for (int m = 0; m < M; ++m) {
        for (int idx = 0; idx < (int)bestOrder[m].size(); ++idx) {
            if (idx) cout << ' ';
            cout << bestOrder[m][idx];
        }
        cout << "\n";
    }
    return 0;
}