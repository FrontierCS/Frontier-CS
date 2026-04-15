#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, v;
    int x;
    int w;
    double logx;
};

struct AdjItem {
    int to;
    int idx;
};

class Solver {
public:
    int n, m, D;
    vector<Edge> edges;
    vector<vector<AdjItem>> adj;
    vector<int> deg;
    int maxDeg = 0;
    double globalMean = 0.0;
    vector<double> nodeInit;
    vector<pair<double,int>> topbuf;

    static constexpr double LIM_A = 1e9;

    inline double clampLog(double x) const {
        static const double LOGMAX = log(1e9);
        if (x < 0.0) return 0.0;
        if (x > LOGMAX) return LOGMAX;
        return x;
    }

    inline double clampReal(double x) const {
        if (x < 1.0) return 1.0;
        if (x > LIM_A) return LIM_A;
        return x;
    }

    inline long long clampInt(long long x) const {
        if (x < 1LL) return 1LL;
        if (x > 1000000000LL) return 1000000000LL;
        return x;
    }

    void readInput() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        cin >> n >> m >> D;

        edges.resize(m);
        deg.assign(n, 0);
        vector<double> nodeSumW(n, 0.0), nodeSumWY(n, 0.0);
        double sumW = 0.0, sumWY = 0.0;

        for (int i = 0; i < m; ++i) {
            int u, v, x, w;
            cin >> u >> v >> x >> w;
            --u; --v;
            double y = log((double)x);
            edges[i] = {u, v, x, w, y};
            deg[u]++; deg[v]++;
            sumW += w;
            sumWY += w * y;
            nodeSumW[u] += w;
            nodeSumWY[u] += w * y;
            nodeSumW[v] += w;
            nodeSumWY[v] += w * y;
        }

        globalMean = (sumW > 0.0 ? sumWY / sumW : 0.0);

        adj.assign(n, {});
        for (int i = 0; i < n; ++i) adj[i].reserve(deg[i]);
        for (int i = 0; i < m; ++i) {
            adj[edges[i].u].push_back({edges[i].v, i});
            adj[edges[i].v].push_back({edges[i].u, i});
        }
        for (int i = 0; i < n; ++i) {
            sort(adj[i].begin(), adj[i].end(), [](const AdjItem& a, const AdjItem& b) {
                return a.to < b.to;
            });
            maxDeg = max(maxDeg, (int)adj[i].size());
        }

        nodeInit.assign(n, clampLog(globalMean * 0.5));
        for (int i = 0; i < n; ++i) {
            if (nodeSumW[i] > 0.0) {
                nodeInit[i] = clampLog(nodeSumWY[i] / nodeSumW[i] - globalMean * 0.5);
            }
        }

        topbuf.reserve(m);
    }

    template <class ErrorFunc>
    void markTopD(ErrorFunc errf, vector<uint8_t>& active) {
        active.assign(m, 1);
        if (D == 0) return;
        topbuf.resize(m);
        for (int i = 0; i < m; ++i) topbuf[i] = {errf(i), i};
        auto nth = topbuf.begin() + (m - D);
        nth_element(topbuf.begin(), nth, topbuf.end(), [](const auto& a, const auto& b) {
            return a.first < b.first;
        });
        for (auto it = nth; it != topbuf.end(); ++it) active[it->second] = 0;
    }

    double weightedMedian(vector<pair<double,double>>& items) const {
        sort(items.begin(), items.end(), [](const auto& a, const auto& b) {
            return a.first < b.first;
        });
        long double total = 0.0;
        for (auto &it : items) total += (long double)it.second;
        long double half = total * 0.5L;
        long double cur = 0.0;
        double ans = items.back().first;
        for (auto &it : items) {
            cur += (long double)it.second;
            if (cur >= half) {
                ans = it.first;
                break;
            }
        }
        return ans;
    }

    vector<uint8_t> robustLogFit(vector<double>& b) {
        vector<uint8_t> active(m, 1);
        vector<double> num(n), den(n);
        const double C = 0.40;
        const double RELAX = 0.70;

        auto doSweep = [&]() {
            fill(num.begin(), num.end(), 0.0);
            fill(den.begin(), den.end(), 0.0);
            for (int i = 0; i < m; ++i) if (active[i]) {
                const Edge &e = edges[i];
                double r = b[e.u] + b[e.v] - e.logx;
                double ar = fabs(r);
                double fac = (ar <= C ? 1.0 : C / ar);
                double alpha = e.w * fac;
                num[e.u] += alpha * (e.logx - b[e.v]);
                den[e.u] += alpha;
                num[e.v] += alpha * (e.logx - b[e.u]);
                den[e.v] += alpha;
            }
            for (int i = 0; i < n; ++i) {
                if (den[i] > 0.0) {
                    double nb = num[i] / den[i];
                    b[i] = clampLog((1.0 - RELAX) * b[i] + RELAX * nb);
                } else {
                    b[i] = clampLog(b[i]);
                }
            }
        };

        doSweep();
        doSweep();

        if (D > 0) {
            markTopD([&](int i) -> double {
                const Edge &e = edges[i];
                double r = b[e.u] + b[e.v] - e.logx;
                return e.w * fabs(expm1(r));
            }, active);
        }

        doSweep();
        doSweep();
        doSweep();
        return active;
    }

    vector<double> buildAnchorSeed() {
        vector<double> b(n, clampLog(globalMean * 0.5));

        const int K = min(64, m);
        using PII = pair<long long,int>;
        priority_queue<PII, vector<PII>, greater<PII>> pq;
        for (int i = 0; i < m; ++i) {
            long long score = 1LL * edges[i].w * 4096LL + min(deg[edges[i].u], deg[edges[i].v]);
            if ((int)pq.size() < K) pq.push({score, i});
            else if (score > pq.top().first) {
                pq.pop();
                pq.push({score, i});
            }
        }
        vector<int> candEdges;
        while (!pq.empty()) {
            candEdges.push_back(pq.top().second);
            pq.pop();
        }
        if (candEdges.empty()) return nodeInit;

        int bestIdx = candEdges[0];
        double bestScore = -1.0;
        double bestDiff = 0.0;

        for (int idx : candEdges) {
            const Edge &e = edges[idx];
            int s = e.u, t = e.v;
            int i = 0, j = 0;
            double support = 0.0, diffSum = 0.0, diffDen = 0.0;
            while (i < (int)adj[s].size() && j < (int)adj[t].size()) {
                if (adj[s][i].to < adj[t][j].to) ++i;
                else if (adj[s][i].to > adj[t][j].to) ++j;
                else {
                    int c = adj[s][i].to;
                    if (c != s && c != t) {
                        int e1 = adj[s][i].idx;
                        int e2 = adj[t][j].idx;
                        double ww = min(edges[e1].w, edges[e2].w);
                        support += ww;
                        diffSum += ww * (edges[e1].logx - edges[e2].logx);
                        diffDen += ww;
                    }
                    ++i; ++j;
                }
            }
            double sc = support + 1e-3 * e.w;
            if (sc > bestScore) {
                bestScore = sc;
                bestIdx = idx;
                bestDiff = (diffDen > 0.0 ? diffSum / diffDen : 0.0);
            }
        }

        const Edge &be = edges[bestIdx];
        int s = be.u, t = be.v;
        b[s] = clampLog((be.logx + bestDiff) * 0.5);
        b[t] = clampLog((be.logx - bestDiff) * 0.5);

        vector<uint8_t> known(n, 0);
        known[s] = known[t] = 1;

        struct SeedNode {
            double score;
            int v;
            double bval;
        };
        vector<SeedNode> extra;
        int i = 0, j = 0;
        while (i < (int)adj[s].size() && j < (int)adj[t].size()) {
            if (adj[s][i].to < adj[t][j].to) ++i;
            else if (adj[s][i].to > adj[t][j].to) ++j;
            else {
                int c = adj[s][i].to;
                if (c != s && c != t) {
                    int e1 = adj[s][i].idx;
                    int e2 = adj[t][j].idx;
                    double ww = min(edges[e1].w, edges[e2].w);
                    double bc = (edges[e1].logx + edges[e2].logx - be.logx) * 0.5;
                    extra.push_back({ww, c, clampLog(bc)});
                }
                ++i; ++j;
            }
        }
        sort(extra.begin(), extra.end(), [](const SeedNode& a, const SeedNode& b) {
            return a.score > b.score;
        });
        for (int k = 0; k < (int)extra.size() && k < 8; ++k) {
            known[extra[k].v] = 1;
            b[extra[k].v] = extra[k].bval;
        }

        vector<double> num(n), den(n);
        for (int pass = 0; pass < 6; ++pass) {
            fill(num.begin(), num.end(), 0.0);
            fill(den.begin(), den.end(), 0.0);
            for (int ei = 0; ei < m; ++ei) {
                const Edge &e = edges[ei];
                if (known[e.u] && !known[e.v]) {
                    num[e.v] += e.w * (e.logx - b[e.u]);
                    den[e.v] += e.w;
                } else if (known[e.v] && !known[e.u]) {
                    num[e.u] += e.w * (e.logx - b[e.v]);
                    den[e.u] += e.w;
                }
            }
            int changed = 0;
            for (int v = 0; v < n; ++v) {
                if (!known[v] && den[v] > 0.0) {
                    b[v] = clampLog(num[v] / den[v]);
                    known[v] = 1;
                    ++changed;
                }
            }
            if (changed == 0) break;
        }

        for (int v = 0; v < n; ++v) {
            if (!known[v]) b[v] = nodeInit[v];
        }
        return b;
    }

    void buildComponents(const vector<uint8_t>& active, vector<int>& comp, vector<vector<int>>& compNodes) {
        comp.assign(n, -1);
        compNodes.clear();
        vector<int> q;
        q.reserve(n);
        for (int s = 0; s < n; ++s) if (comp[s] == -1) {
            int cid = (int)compNodes.size();
            compNodes.push_back({});
            comp[s] = cid;
            q.clear();
            q.push_back(s);
            for (int head = 0; head < (int)q.size(); ++head) {
                int u = q[head];
                compNodes[cid].push_back(u);
                for (const auto& ae : adj[u]) if (active[ae.idx]) {
                    int v = ae.to;
                    if (comp[v] == -1) {
                        comp[v] = cid;
                        q.push_back(v);
                    }
                }
            }
        }
    }

    void componentScale(vector<double>& a, const vector<uint8_t>& active) {
        vector<int> comp;
        vector<vector<int>> compNodes;
        buildComponents(active, comp, compNodes);
        vector<vector<pair<double,double>>> vals(compNodes.size());
        for (int i = 0; i < m; ++i) if (active[i]) {
            const Edge &e = edges[i];
            int c = comp[e.u];
            long double p = (long double)a[e.u] * (long double)a[e.v];
            if (p <= 0.0L) continue;
            double t = (double)((long double)e.x / p);
            double w = (double)((long double)e.w * p / (long double)e.x);
            vals[c].push_back({t, w});
        }
        for (int c = 0; c < (int)compNodes.size(); ++c) {
            if (vals[c].empty()) continue;
            double z = weightedMedian(vals[c]);
            if (z < 1e-18) z = 1e-18;
            double scale = sqrt(z);
            if (fabs(scale - 1.0) < 1e-14) continue;
            for (int v : compNodes[c]) a[v] = clampReal(a[v] * scale);
        }
    }

    void exactMedianSweep(vector<double>& a, const vector<uint8_t>& active, int sweeps) {
        vector<pair<double,double>> items;
        items.reserve(maxDeg);
        for (int it = 0; it < sweeps; ++it) {
            for (int i = 0; i < n; ++i) {
                items.clear();
                for (const auto& ae : adj[i]) if (active[ae.idx]) {
                    const Edge &e = edges[ae.idx];
                    double aj = a[ae.to];
                    if (aj <= 0.0) continue;
                    double t = (double)e.x / aj;
                    double w = (double)e.w * aj / (double)e.x;
                    items.push_back({t, w});
                }
                if (items.empty()) continue;
                double med = weightedMedian(items);
                a[i] = clampReal(med);
            }
        }
    }

    vector<long long> roundToInt(const vector<double>& a) const {
        vector<long long> ai(n, 1);
        for (int i = 0; i < n; ++i) {
            long double v = a[i];
            if (v < 1.0L) v = 1.0L;
            if (v > 1e9L) v = 1e9L;
            long long x = (long long) llround((double)v);
            ai[i] = clampInt(x);
        }
        return ai;
    }

    long double localNodeCost(int i, long long cand, const vector<long long>& ai, const vector<uint8_t>& active) const {
        long double sum = 0.0L;
        for (const auto& ae : adj[i]) if (active[ae.idx]) {
            const Edge &e = edges[ae.idx];
            long double p = (long double)cand * (long double)ai[ae.to];
            sum += (long double)e.w * fabsl(p - (long double)e.x) / (long double)e.x;
        }
        return sum;
    }

    void integerCoordinateSweep(vector<long long>& ai, const vector<uint8_t>& active, int sweeps) {
        vector<pair<double,double>> items;
        items.reserve(maxDeg);
        for (int it = 0; it < sweeps; ++it) {
            for (int i = 0; i < n; ++i) {
                items.clear();
                for (const auto& ae : adj[i]) if (active[ae.idx]) {
                    const Edge &e = edges[ae.idx];
                    long long aj = ai[ae.to];
                    if (aj <= 0) continue;
                    double t = (double)e.x / (double)aj;
                    double w = (double)e.w * (double)aj / (double)e.x;
                    items.push_back({t, w});
                }
                if (items.empty()) continue;
                double med = weightedMedian(items);
                long long c1 = clampInt((long long)floor(med));
                long long c2 = clampInt((long long)ceil(med));
                long long cur = ai[i];
                long long cand[3] = {cur, c1, c2};
                sort(cand, cand + 3);
                long long best = cur;
                long double bestCost = localNodeCost(i, cur, ai, active);
                for (int z = 0; z < 3; ++z) {
                    if (z > 0 && cand[z] == cand[z - 1]) continue;
                    long double cst = localNodeCost(i, cand[z], ai, active);
                    if (cst < bestCost) {
                        bestCost = cst;
                        best = cand[z];
                    }
                }
                ai[i] = best;
            }
        }
    }

    vector<long long> buildCandidate(const vector<double>& initB) {
        vector<double> b = initB;
        for (double &x : b) x = clampLog(x);

        vector<uint8_t> activeLog = robustLogFit(b);

        vector<double> a(n, 1.0);
        for (int i = 0; i < n; ++i) {
            double z = exp(clampLog(b[i]));
            a[i] = clampReal(z);
        }

        componentScale(a, activeLog);

        vector<uint8_t> activeExact;
        markTopD([&](int i) -> double {
            const Edge &e = edges[i];
            long double p = (long double)a[e.u] * (long double)a[e.v];
            return (double)((long double)e.w * fabsl(p - (long double)e.x) / (long double)e.x);
        }, activeExact);

        exactMedianSweep(a, activeExact, 1);
        componentScale(a, activeExact);

        vector<long long> ai = roundToInt(a);
        integerCoordinateSweep(ai, activeExact, 1);

        for (int i = 0; i < n; ++i) if (deg[i] == 0) ai[i] = 1;
        return ai;
    }

    pair<long double, vector<int>> evaluateExact(const vector<long long>& ai, bool needIndices) {
        long double total = 0.0L;
        if (D == 0) {
            for (int i = 0; i < m; ++i) {
                const Edge &e = edges[i];
                long double p = (long double)ai[e.u] * (long double)ai[e.v];
                total += (long double)e.w * fabsl(p - (long double)e.x) / (long double)e.x;
            }
            return {total, {}};
        }

        topbuf.resize(m);
        for (int i = 0; i < m; ++i) {
            const Edge &e = edges[i];
            long double p = (long double)ai[e.u] * (long double)ai[e.v];
            double err = (double)((long double)e.w * fabsl(p - (long double)e.x) / (long double)e.x);
            total += (long double)err;
            topbuf[i] = {err, i};
        }

        auto nth = topbuf.begin() + (m - D);
        nth_element(topbuf.begin(), nth, topbuf.end(), [](const auto& a, const auto& b) {
            return a.first < b.first;
        });

        long double removed = 0.0L;
        vector<int> idxs;
        if (needIndices) idxs.reserve(D);
        for (auto it = nth; it != topbuf.end(); ++it) {
            removed += (long double)it->first;
            if (needIndices) idxs.push_back(it->second + 1);
        }
        if (needIndices) sort(idxs.begin(), idxs.end());
        return {total - removed, idxs};
    }

    void solve() {
        readInput();

        vector<long long> bestA(n, 1);
        auto bestEval = evaluateExact(bestA, false);
        long double bestLoss = bestEval.first;

        vector<long long> cand1 = buildCandidate(nodeInit);
        auto ev1 = evaluateExact(cand1, false);
        if (ev1.first < bestLoss) {
            bestLoss = ev1.first;
            bestA = move(cand1);
        }

        vector<double> seed2 = buildAnchorSeed();
        vector<long long> cand2 = buildCandidate(seed2);
        auto ev2 = evaluateExact(cand2, false);
        if (ev2.first < bestLoss) {
            bestLoss = ev2.first;
            bestA = move(cand2);
        }

        auto finalEval = evaluateExact(bestA, true);
        const vector<int>& discards = finalEval.second;

        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << bestA[i];
        }
        cout << '\n';

        cout << discards.size();
        for (int idx : discards) cout << ' ' << idx;
        cout << '\n';
    }
};

int main() {
    Solver solver;
    solver.solve();
    return 0;
}