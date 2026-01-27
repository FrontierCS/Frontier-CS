#include <bits/stdc++.h>
using namespace std;

struct Device {
    int id;
    int x, y;
    char type;
};

static inline long long dist2_ll(int x1, int y1, int x2, int y2) {
    long long dx = (long long)x1 - x2;
    long long dy = (long long)y1 - y2;
    return dx*dx + dy*dy;
}

static inline double rr_weight(const Device& a, const Device& b) {
    double factor = (a.type == 'R' && b.type == 'R') ? 1.0 : 0.8;
    return factor * (double)dist2_ll(a.x, a.y, b.x, b.y);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, K;
    if (!(cin >> N >> K)) {
        return 0;
    }
    vector<Device> robots;
    vector<Device> relays;
    robots.reserve(N);
    relays.reserve(K);
    for (int i = 0; i < N + K; ++i) {
        Device d;
        string t;
        cin >> d.id >> d.x >> d.y >> t;
        d.type = t[0];
        if (d.type == 'C') relays.push_back(d);
        else robots.push_back(d);
    }
    int R = (int)robots.size();
    int C = (int)relays.size();

    // Handle trivial case
    if (R == 0) {
        cout << "#\n#\n";
        return 0;
    }
    if (R == 1) {
        cout << "#\n#\n";
        return 0;
    }

    // Prim's algorithm on robots only
    const double INF = 1e300;
    vector<double> key(R, INF);
    vector<int> parent(R, -1);
    vector<char> inMST(R, 0);
    key[0] = 0.0;

    for (int it = 0; it < R; ++it) {
        int u = -1;
        double best = INF;
        for (int i = 0; i < R; ++i) {
            if (!inMST[i] && key[i] < best) {
                best = key[i];
                u = i;
            }
        }
        if (u == -1) break;
        inMST[u] = 1;
        for (int v = 0; v < R; ++v) {
            if (!inMST[v]) {
                double w = rr_weight(robots[u], robots[v]);
                if (w < key[v]) {
                    key[v] = w;
                    parent[v] = u;
                }
            }
        }
    }

    // Build MST edge list (robot indices)
    vector<pair<int,int>> mstEdges;
    mstEdges.reserve(R - 1);
    for (int i = 0; i < R; ++i) {
        if (parent[i] != -1) {
            mstEdges.emplace_back(i, parent[i]);
        }
    }

    // Precompute dist^2 from each relay to each robot
    vector<vector<long long>> d2CR;
    if (C > 0) {
        d2CR.assign(C, vector<long long>(R, 0));
        for (int j = 0; j < C; ++j) {
            for (int i = 0; i < R; ++i) {
                d2CR[j][i] = dist2_ll(relays[j].x, relays[j].y, robots[i].x, robots[i].y);
            }
        }
    }

    struct EdgeCand {
        int eidx;
        int u, v;
        double baseCost;
        int bestC;
        double bestCost;
        double saving;
    };

    vector<EdgeCand> cands;
    if (C > 0) {
        for (int ei = 0; ei < (int)mstEdges.size(); ++ei) {
            int u = mstEdges[ei].first;
            int v = mstEdges[ei].second;
            double base = rr_weight(robots[u], robots[v]);
            long long bestSumLL = LLONG_MAX;
            int bestJ = -1;
            for (int j = 0; j < C; ++j) {
                long long sum = d2CR[j][u] + d2CR[j][v];
                if (sum < bestSumLL) {
                    bestSumLL = sum;
                    bestJ = j;
                }
            }
            if (bestJ != -1) {
                double bestSum = (double)bestSumLL; // factor 1.0 for both robot-relay edges
                double saving = base - bestSum;
                if (saving > 1e-9) {
                    EdgeCand ec;
                    ec.eidx = ei;
                    ec.u = u; ec.v = v;
                    ec.baseCost = base;
                    ec.bestC = bestJ;
                    ec.bestCost = bestSum;
                    ec.saving = saving;
                    cands.push_back(ec);
                }
            }
        }
        sort(cands.begin(), cands.end(), [](const EdgeCand& a, const EdgeCand& b){
            if (a.saving == b.saving) return a.eidx < b.eidx;
            return a.saving > b.saving;
        });
    }

    vector<int> replacedByC(mstEdges.size(), -1);
    vector<char> usedC(C, 0);

    for (auto &cand : cands) {
        int eidx = cand.eidx;
        if (replacedByC[eidx] != -1) continue;
        int u = cand.u, v = cand.v;
        double base = cand.baseCost;
        int chC = -1;
        double bestCost = 0.0;
        if (cand.bestC >= 0 && !usedC[cand.bestC]) {
            chC = cand.bestC;
            bestCost = cand.bestCost;
        } else {
            long long bestSumLL = LLONG_MAX;
            int bestJ = -1;
            for (int j = 0; j < C; ++j) {
                if (usedC[j]) continue;
                long long sum = d2CR[j][u] + d2CR[j][v];
                if (sum < bestSumLL) {
                    bestSumLL = sum;
                    bestJ = j;
                }
            }
            if (bestJ != -1) {
                double bestSum = (double)bestSumLL;
                if (base - bestSum > 1e-9) {
                    chC = bestJ;
                    bestCost = bestSum;
                }
            }
        }
        if (chC != -1) {
            usedC[chC] = 1;
            replacedByC[eidx] = chC;
        }
    }

    // Prepare output
    vector<int> selectedCIDs;
    for (int j = 0; j < C; ++j) {
        if (usedC[j]) selectedCIDs.push_back(relays[j].id);
    }

    if (selectedCIDs.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < selectedCIDs.size(); ++i) {
            if (i) cout << '#';
            cout << selectedCIDs[i];
        }
        cout << '\n';
    }

    vector<pair<int,int>> links;
    links.reserve(mstEdges.size() + selectedCIDs.size());
    for (int ei = 0; ei < (int)mstEdges.size(); ++ei) {
        int u = mstEdges[ei].first;
        int v = mstEdges[ei].second;
        if (replacedByC[ei] == -1) {
            links.emplace_back(robots[u].id, robots[v].id);
        } else {
            int cj = replacedByC[ei];
            links.emplace_back(robots[u].id, relays[cj].id);
            links.emplace_back(robots[v].id, relays[cj].id);
        }
    }

    if (links.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < links.size(); ++i) {
            if (i) cout << '#';
            cout << links[i].first << '-' << links[i].second;
        }
        cout << '\n';
    }

    return 0;
}