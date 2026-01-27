#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
    int idx;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string input, line;
    {
        ostringstream ss;
        ss << cin.rdbuf();
        input = ss.str();
    }

    // Parse JSON using regex
    regex re("\\\"([^\\\"]+)\\\"\\s*:\\s*\\[\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)\\s*\\]");
    sregex_iterator it(input.begin(), input.end(), re);
    sregex_iterator end;
    vector<Item> items;
    int idx = 0;
    for (; it != end; ++it) {
        smatch m;
        m = *it;
        Item itx;
        itx.name = m[1];
        itx.q = stoll(m[2]);
        itx.v = stoll(m[3]);
        itx.m = stoll(m[4]);
        itx.l = stoll(m[5]);
        itx.idx = idx++;
        items.push_back(itx);
    }
    if (items.empty()) {
        // Fallback: empty output
        cout << "{\n}\n";
        return 0;
    }

    const long long CAP_M = 20000000LL;
    const long long CAP_L = 25000000LL;
    int n = (int)items.size();

    auto greedy_by = [&](vector<double> density)->pair<vector<long long>, long long> {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        stable_sort(order.begin(), order.end(), [&](int a, int b){
            if (density[a] == density[b]) return a < b;
            return density[a] > density[b];
        });
        vector<long long> cnt(n, 0);
        long long remM = CAP_M, remL = CAP_L;
        long long totalV = 0;
        for (int id : order) {
            const Item &itx = items[id];
            if (itx.m == 0 || itx.l == 0) continue; // should not happen per problem
            long long t1 = remM / itx.m;
            long long t2 = remL / itx.l;
            long long t = min({itx.q, t1, t2});
            if (t <= 0) continue;
            cnt[id] += t;
            remM -= t * itx.m;
            remL -= t * itx.l;
            totalV += t * itx.v;
        }
        return {cnt, totalV};
    };

    auto compute_density = [&](double lambda)->vector<double> {
        vector<double> d(n);
        for (int i = 0; i < n; ++i) {
            double wm = (double)items[i].m / (double)CAP_M;
            double wl = (double)items[i].l / (double)CAP_L;
            double w = lambda * wm + (1.0 - lambda) * wl;
            if (w == 0) w = 1e-18;
            d[i] = (double)items[i].v / w;
        }
        return d;
    };

    vector<pair<string,long long>> bestAns; bestAns.reserve(n);
    vector<long long> bestCnt(n, 0);
    long long bestV = -1;

    // Try multiple heuristics
    vector<double> lambdas = {0.0, 0.25, 0.5, 0.75, 1.0};
    for (double lam : lambdas) {
        auto dens = compute_density(lam);
        auto res = greedy_by(dens);
        if (res.second > bestV) {
            bestV = res.second;
            bestCnt = move(res.first);
        }
    }
    // v / max(wm, wl)
    {
        vector<double> d(n);
        for (int i = 0; i < n; ++i) {
            double wm = (double)items[i].m / (double)CAP_M;
            double wl = (double)items[i].l / (double)CAP_L;
            double w = max(wm, wl);
            if (w == 0) w = 1e-18;
            d[i] = (double)items[i].v / w;
        }
        auto res = greedy_by(d);
        if (res.second > bestV) {
            bestV = res.second;
            bestCnt = move(res.first);
        }
    }
    // v/m and v/l
    {
        vector<double> d(n);
        for (int i = 0; i < n; ++i) {
            double w = (double)items[i].m / (double)CAP_M;
            if (w == 0) w = 1e-18;
            d[i] = (double)items[i].v / w;
        }
        auto res = greedy_by(d);
        if (res.second > bestV) {
            bestV = res.second;
            bestCnt = move(res.first);
        }
    }
    {
        vector<double> d(n);
        for (int i = 0; i < n; ++i) {
            double w = (double)items[i].l / (double)CAP_L;
            if (w == 0) w = 1e-18;
            d[i] = (double)items[i].v / w;
        }
        auto res = greedy_by(d);
        if (res.second > bestV) {
            bestV = res.second;
            bestCnt = move(res.first);
        }
    }

    auto calcUsed = [&](const vector<long long>& cnt){
        long long um=0, ul=0, uv=0;
        for (int i=0;i<n;++i){
            um += cnt[i]*items[i].m;
            ul += cnt[i]*items[i].l;
            uv += cnt[i]*items[i].v;
        }
        return tuple<long long,long long,long long>(um,ul,uv);
    };

    // Local improvement
    {
        auto [usedM, usedL, usedV] = calcUsed(bestCnt);
        // Attempt direct additions where possible
        auto scoreDensity = [&](int i)->double{
            double wm = (double)items[i].m / (double)CAP_M;
            double wl = (double)items[i].l / (double)CAP_L;
            double w = wm + wl;
            if (w == 0) w = 1e-18;
            return (double)items[i].v / w;
        };
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a,int b){ return scoreDensity(a) > scoreDensity(b); });

        bool improved = true;
        int iter = 0;
        while (improved && iter < 200) {
            improved = false;
            ++iter;
            for (int j : order) {
                if (bestCnt[j] >= items[j].q) continue;
                long long nm = usedM + items[j].m;
                long long nl = usedL + items[j].l;
                if (nm <= CAP_M && nl <= CAP_L) {
                    bestCnt[j] += 1;
                    usedM = nm; usedL = nl; usedV += items[j].v;
                    improved = true;
                    continue;
                }
                long long needM = max(0LL, nm - CAP_M);
                long long needL = max(0LL, nl - CAP_L);
                if (needM<=0 && needL<=0) {
                    bestCnt[j] += 1;
                    usedM = nm; usedL = nl; usedV += items[j].v;
                    improved = true;
                    continue;
                }
                // Prepare removal list
                struct Cand { int i; double eff; double costw; };
                vector<Cand> cands;
                double alpha = 1.0 / max(1.0, (double)needM);
                double beta  = 1.0 / max(1.0, (double)needL);
                for (int i = 0; i < n; ++i) {
                    if (bestCnt[i] <= 0) continue;
                    double cw = alpha * (double)items[i].m + beta * (double)items[i].l;
                    double eff = (cw <= 0 ? 1e18 : (double)items[i].v / cw);
                    cands.push_back({i, eff, cw});
                }
                if (cands.empty()) continue;
                sort(cands.begin(), cands.end(), [&](const Cand& A, const Cand& B){
                    if (A.eff == B.eff) return A.i < B.i;
                    return A.eff < B.eff; // remove least efficient value per cost first
                });
                long long rmM = 0, rmL = 0, lossV = 0;
                vector<pair<int,long long>> toRemove;
                long long needMm = needM, needLl = needL;
                for (auto &c : cands) {
                    if (needMm <= 0 && needLl <= 0) break;
                    int i = c.i;
                    long long avail = bestCnt[i];
                    if (avail <= 0) continue;
                    long long reqM = (needMm > 0 ? ( (needMm + items[i].m - 1) / items[i].m ) : 0);
                    long long reqL = (needLl > 0 ? ( (needLl + items[i].l - 1) / items[i].l ) : 0);
                    long long r = max(reqM, reqL);
                    if (r <= 0) continue;
                    if (r > avail) r = avail;
                    rmM += r * items[i].m;
                    rmL += r * items[i].l;
                    lossV += r * items[i].v;
                    needMm -= r * items[i].m;
                    needLl -= r * items[i].l;
                    toRemove.push_back({i, r});
                }
                if (needMm <= 0 && needLl <= 0) {
                    if (items[j].v > lossV) {
                        // apply
                        for (auto &p : toRemove) bestCnt[p.first] -= p.second;
                        bestCnt[j] += 1;
                        usedM = usedM - rmM + items[j].m;
                        usedL = usedL - rmL + items[j].l;
                        usedV = usedV - lossV + items[j].v;
                        improved = true;
                    }
                }
            }
        }
        bestV = usedV;
    }

    // Prepare output in the same order as parsed
    cout << "{\n";
    for (int i = 0; i < n; ++i) {
        cout << " \"" << items[i].name << "\": " << bestCnt[i];
        if (i + 1 < n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";
    return 0;
}