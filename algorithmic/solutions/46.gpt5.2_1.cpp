#include <bits/stdc++.h>
using namespace std;

static const long long INF = (1LL << 62);

static inline long long addSat(long long a, long long b) {
    __int128 s = ( __int128)a + ( __int128)b;
    if (s > (__int128)INF) return INF;
    return (long long)s;
}

struct Instance {
    int J, M;
    vector<vector<int>> mach;   // [j][k]
    vector<vector<long long>> dur; // [j][k]
    vector<vector<int>> pos;    // [j][m] -> k
    vector<vector<long long>> rem; // [j][k] remaining sum from k..end
    vector<long long> nodeDur;  // size N
    vector<int> jobPred, jobSucc;
    vector<int> opId; // size J*M: node id = j*M+k => itself, but keep for clarity
};

struct Solution {
    vector<vector<int>> order; // [m][i] job
    long long makespan = INF;
};

static long long evaluateMakespan(const Instance& ins, const vector<vector<int>>& order) {
    const int J = ins.J, M = ins.M;
    const int N = J * M;

    vector<int> machinePred(N, -1), machineSucc(N, -1);
    for (int m = 0; m < M; m++) {
        for (int i = 0; i < J; i++) {
            int j = order[m][i];
            int k = ins.pos[j][m];
            int v = j * M + k;
            if (i > 0) {
                int jp = order[m][i - 1];
                int kp = ins.pos[jp][m];
                int u = jp * M + kp;
                machinePred[v] = u;
                machineSucc[u] = v;
            }
        }
    }

    vector<int> indeg(N, 0);
    for (int v = 0; v < N; v++) {
        if (ins.jobPred[v] != -1) indeg[v]++;
        if (machinePred[v] != -1) indeg[v]++;
    }

    deque<int> dq;
    dq.clear();
    for (int v = 0; v < N; v++) if (indeg[v] == 0) dq.push_back(v);

    vector<long long> st(N, 0);
    int processed = 0;
    long long makespan = 0;

    while (!dq.empty()) {
        int u = dq.front();
        dq.pop_front();
        processed++;

        long long fin = addSat(st[u], ins.nodeDur[u]);
        if (fin > makespan) makespan = fin;

        int vs[2] = {ins.jobSucc[u], machineSucc[u]};
        for (int t = 0; t < 2; t++) {
            int v = vs[t];
            if (v == -1) continue;
            if (fin > st[v]) st[v] = fin;
            if (--indeg[v] == 0) dq.push_back(v);
        }
    }

    if (processed != N) return INF; // cycle
    return makespan;
}

enum class HeuMode {
    EST_SPT,
    EST_LPT,
    ECT_SPT,
    EST_MWKR,
    RANDOM_LINEAR
};

static vector<vector<int>> serialSGS(const Instance& ins, HeuMode mode, mt19937_64& rng,
                                    double w1 = 1.0, double w2 = 0.0, double w3 = 0.0) {
    const int J = ins.J, M = ins.M;
    const int N = J * M;

    vector<int> idx(J, 0);
    vector<long long> jobT(J, 0), macT(M, 0);
    vector<vector<int>> order(M);
    for (int m = 0; m < M; m++) order[m].clear(), order[m].reserve(J);

    uniform_real_distribution<double> ur(0.0, 1.0);

    for (int step = 0; step < N; step++) {
        int bestJ = -1;
        long long bestEst = 0, bestP = 0, bestECT = 0, bestRem = 0;
        long double bestKey = 0;
        tuple<long long,long long,long long,long long> bestTie{0,0,0,0};

        for (int j = 0; j < J; j++) {
            int k = idx[j];
            if (k >= M) continue;
            int m = ins.mach[j][k];
            long long p = ins.dur[j][k];
            long long est = max(jobT[j], macT[m]);
            long long ect = addSat(est, p);
            long long rem = ins.rem[j][k];

            bool take = false;
            if (mode == HeuMode::EST_SPT) {
                auto tie = make_tuple(est, p, ect, (long long)j);
                if (bestJ == -1 || tie < bestTie) { take = true; bestTie = tie; }
            } else if (mode == HeuMode::EST_LPT) {
                auto tie = make_tuple(est, -p, ect, (long long)j);
                if (bestJ == -1 || tie < bestTie) { take = true; bestTie = tie; }
            } else if (mode == HeuMode::ECT_SPT) {
                auto tie = make_tuple(ect, est, p, (long long)j);
                if (bestJ == -1 || tie < bestTie) { take = true; bestTie = tie; }
            } else if (mode == HeuMode::EST_MWKR) {
                auto tie = make_tuple(est, -rem, p, (long long)j);
                if (bestJ == -1 || tie < bestTie) { take = true; bestTie = tie; }
            } else { // RANDOM_LINEAR
                // minimize w1*est + w2*p - w3*rem (+ tiny noise)
                long double key = (long double)w1 * (long double)est + (long double)w2 * (long double)p
                                - (long double)w3 * (long double)rem
                                + (long double)(1e-9 * ur(rng));
                if (bestJ == -1 || key < bestKey) { take = true; bestKey = key; }
                else if (fabsl(key - bestKey) < 1e-12L) {
                    // deterministic tiebreak
                    auto tie = make_tuple(est, p, ect, (long long)j);
                    auto curTie = make_tuple(bestEst, bestP, bestECT, (long long)bestJ);
                    if (tie < curTie) take = true;
                }
            }

            if (take) {
                bestJ = j;
                bestEst = est;
                bestP = p;
                bestECT = ect;
                bestRem = rem;
            }
        }

        int j = bestJ;
        int k = idx[j];
        int m = ins.mach[j][k];
        long long p = ins.dur[j][k];
        long long st = max(jobT[j], macT[m]);
        long long fin = addSat(st, p);
        jobT[j] = fin;
        macT[m] = fin;
        idx[j]++;

        order[m].push_back(j);
    }

    // sanity: fill missing if any (shouldn't happen)
    for (int m = 0; m < M; m++) {
        if ((int)order[m].size() != J) {
            vector<int> used(J, 0);
            for (int x : order[m]) if (0 <= x && x < J) used[x] = 1;
            for (int j = 0; j < J; j++) if (!used[j]) order[m].push_back(j);
            if ((int)order[m].size() > J) order[m].resize(J);
        }
    }
    return order;
}

static bool isPermutationPerMachine(const vector<vector<int>>& order, int J, int M) {
    if ((int)order.size() != M) return false;
    for (int m = 0; m < M; m++) {
        if ((int)order[m].size() != J) return false;
        vector<int> seen(J, 0);
        for (int j : order[m]) {
            if (j < 0 || j >= J) return false;
            if (seen[j]++) return false;
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Instance ins;
    if (!(cin >> ins.J >> ins.M)) return 0;
    int J = ins.J, M = ins.M;
    ins.mach.assign(J, vector<int>(M));
    ins.dur.assign(J, vector<long long>(M));
    ins.pos.assign(J, vector<int>(M, -1));
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            int m; long long p;
            cin >> m >> p;
            ins.mach[j][k] = m;
            ins.dur[j][k] = p;
            ins.pos[j][m] = k;
        }
    }

    ins.rem.assign(J, vector<long long>(M, 0));
    for (int j = 0; j < J; j++) {
        long long s = 0;
        for (int k = M - 1; k >= 0; k--) {
            s = addSat(s, ins.dur[j][k]);
            ins.rem[j][k] = s;
        }
    }

    int N = J * M;
    ins.nodeDur.assign(N, 0);
    ins.jobPred.assign(N, -1);
    ins.jobSucc.assign(N, -1);
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            int id = j * M + k;
            ins.nodeDur[id] = ins.dur[j][k];
            if (k > 0) ins.jobPred[id] = j * M + (k - 1);
            if (k + 1 < M) ins.jobSucc[id] = j * M + (k + 1);
        }
    }

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto startTime = chrono::steady_clock::now();
    auto timeLimit = startTime + chrono::milliseconds(1850);

    Solution best;
    best.order.assign(M, vector<int>(J));
    for (int m = 0; m < M; m++) iota(best.order[m].begin(), best.order[m].end(), 0);
    best.makespan = evaluateMakespan(ins, best.order);
    if (best.makespan >= INF) {
        best.makespan = INF - 1;
    }

    // Candidate: same global job order sorted by total processing time desc
    {
        vector<pair<long long,int>> tot(J);
        for (int j = 0; j < J; j++) {
            long long s = 0;
            for (int k = 0; k < M; k++) s = addSat(s, ins.dur[j][k]);
            tot[j] = {s, j};
        }
        sort(tot.begin(), tot.end(), [&](auto &a, auto &b){
            if (a.first != b.first) return a.first > b.first;
            return a.second < b.second;
        });
        vector<int> global(J);
        for (int i = 0; i < J; i++) global[i] = tot[i].second;
        vector<vector<int>> ord(M, global);
        long long ms = evaluateMakespan(ins, ord);
        if (ms < best.makespan) { best.makespan = ms; best.order = ord; }
    }

    // Candidate: per-machine SPT by processing time
    {
        vector<vector<int>> ord(M, vector<int>(J));
        for (int m = 0; m < M; m++) {
            vector<pair<long long,int>> v;
            v.reserve(J);
            for (int j = 0; j < J; j++) {
                int k = ins.pos[j][m];
                v.push_back({ins.dur[j][k], j});
            }
            sort(v.begin(), v.end(), [&](auto &a, auto &b){
                if (a.first != b.first) return a.first < b.first;
                return a.second < b.second;
            });
            for (int i = 0; i < J; i++) ord[m][i] = v[i].second;
        }
        long long ms = evaluateMakespan(ins, ord);
        if (ms < best.makespan) { best.makespan = ms; best.order = ord; }
    }

    // Several deterministic SGS runs
    vector<HeuMode> modes = {HeuMode::EST_SPT, HeuMode::EST_LPT, HeuMode::ECT_SPT, HeuMode::EST_MWKR};
    for (auto md : modes) {
        auto ord = serialSGS(ins, md, rng);
        if (!isPermutationPerMachine(ord, J, M)) continue;
        long long ms = evaluateMakespan(ins, ord);
        if (ms < best.makespan) { best.makespan = ms; best.order = ord; }
    }

    // Random linear SGS runs
    {
        uniform_real_distribution<double> ud01(0.0, 1.0);
        int tries = 40;
        for (int t = 0; t < tries; t++) {
            if (chrono::steady_clock::now() > timeLimit) break;
            double w1 = 0.1 + 3.0 * ud01(rng);
            double w2 = 0.0 + 2.0 * ud01(rng);
            double w3 = 0.0 + 2.0 * ud01(rng);
            auto ord = serialSGS(ins, HeuMode::RANDOM_LINEAR, rng, w1, w2, w3);
            if (!isPermutationPerMachine(ord, J, M)) continue;
            long long ms = evaluateMakespan(ins, ord);
            if (ms < best.makespan) { best.makespan = ms; best.order = ord; }
        }
    }

    // Local search (SA-ish) on best
    {
        vector<vector<int>> cur = best.order;
        long long curMs = best.makespan;

        vector<vector<int>> bestLS = best.order;
        long long bestLSms = best.makespan;

        uniform_int_distribution<int> dm(0, M - 1);
        uniform_int_distribution<int> djpos(0, max(0, J - 2));
        uniform_real_distribution<double> ur(0.0, 1.0);

        double T = max(1.0, (double)curMs * 0.05);
        double cool = 0.99995;

        long long it = 0;
        while (chrono::steady_clock::now() < timeLimit) {
            it++;
            int m = dm(rng);
            if (J < 2) break;
            int i = djpos(rng);

            int a = cur[m][i], b = cur[m][i + 1];
            if (a == b) continue;
            swap(cur[m][i], cur[m][i + 1]);

            long long ms = evaluateMakespan(ins, cur);
            if (ms >= INF) {
                swap(cur[m][i], cur[m][i + 1]);
            } else {
                long long delta = ms - curMs;
                bool accept = false;
                if (delta <= 0) accept = true;
                else {
                    double Td = max(1e-9, T);
                    if (delta < (long long)(50.0 * Td)) {
                        double prob = exp(-(double)delta / Td);
                        accept = (ur(rng) < prob);
                    } else accept = false;
                }

                if (accept) {
                    curMs = ms;
                    if (ms < bestLSms) {
                        bestLSms = ms;
                        bestLS = cur;
                    }
                } else {
                    swap(cur[m][i], cur[m][i + 1]);
                }
            }

            T *= cool;
            if (T < 1.0) T = 1.0;

            // occasional restart to best to intensify
            if ((it % 5000) == 0 && ur(rng) < 0.3) {
                cur = bestLS;
                curMs = bestLSms;
                T = max(1.0, (double)curMs * 0.03);
            }
        }

        if (bestLSms < best.makespan) {
            best.makespan = bestLSms;
            best.order = bestLS;
        }
    }

    // Fallback safety
    if (!isPermutationPerMachine(best.order, J, M) || evaluateMakespan(ins, best.order) >= INF) {
        best.order.assign(M, vector<int>(J));
        for (int m = 0; m < M; m++) iota(best.order[m].begin(), best.order[m].end(), 0);
    }

    for (int m = 0; m < M; m++) {
        for (int i = 0; i < J; i++) {
            if (i) cout << ' ';
            cout << best.order[m][i];
        }
        cout << '\n';
    }

    return 0;
}