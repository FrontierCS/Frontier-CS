#include <bits/stdc++.h>
using namespace std;

static const long long CAP_M = 20000000LL;
static const long long CAP_V = 25000000LL;

struct Item {
    string name;
    int q;
    long long v;
    long long m;
    long long l;
};

struct Bundle {
    int type;
    int cnt;
    int mU;
    int vU;
    long long val;
};

struct State {
    int mU;
    int vU;
    long long val;
    int prev;
    int bundle;
};

struct FenwickMax {
    int n;
    vector<long long> bit;
    FenwickMax(int n_ = 0) { init(n_); }
    void init(int n_) {
        n = n_;
        bit.assign(n + 1, 0);
    }
    void update(int i, long long v) {
        for (; i <= n; i += i & -i) bit[i] = max(bit[i], v);
    }
    long long query(int i) const {
        long long r = 0;
        for (; i > 0; i -= i & -i) r = max(r, bit[i]);
        return r;
    }
};

struct Solution {
    vector<int> cnt;
    long long value = 0;
    long long mass = 0;
    long long vol = 0;
};

static inline void skipWS(const string& s, size_t& i) {
    while (i < s.size() && (unsigned char)s[i] <= 32) i++;
}

static inline bool consumeChar(const string& s, size_t& i, char c) {
    skipWS(s, i);
    if (i < s.size() && s[i] == c) { i++; return true; }
    return false;
}

static string parseString(const string& s, size_t& i) {
    skipWS(s, i);
    if (i >= s.size() || s[i] != '"') return "";
    i++;
    string out;
    while (i < s.size()) {
        char c = s[i++];
        if (c == '"') break;
        if (c == '\\') {
            if (i >= s.size()) break;
            char e = s[i++];
            if (e == '"' || e == '\\' || e == '/') out.push_back(e);
            else if (e == 'b') out.push_back('\b');
            else if (e == 'f') out.push_back('\f');
            else if (e == 'n') out.push_back('\n');
            else if (e == 'r') out.push_back('\r');
            else if (e == 't') out.push_back('\t');
            else if (e == 'u') {
                // minimal: consume 4 hex digits, ignore unicode properly
                for (int k = 0; k < 4 && i < s.size(); k++) i++;
                out.push_back('?');
            }
        } else {
            out.push_back(c);
        }
    }
    return out;
}

static long long parseInt(const string& s, size_t& i) {
    skipWS(s, i);
    long long x = 0;
    bool neg = false;
    if (i < s.size() && s[i] == '-') { neg = true; i++; }
    while (i < s.size() && isdigit((unsigned char)s[i])) {
        x = x * 10 + (s[i] - '0');
        i++;
    }
    return neg ? -x : x;
}

static bool parseInputJSON(const string& s, vector<Item>& items) {
    size_t i = 0;
    skipWS(s, i);
    if (!consumeChar(s, i, '{')) return false;
    items.clear();
    while (true) {
        skipWS(s, i);
        if (i >= s.size()) return false;
        if (s[i] == '}') { i++; break; }
        string key = parseString(s, i);
        if (key.empty()) return false;
        if (!consumeChar(s, i, ':')) return false;
        if (!consumeChar(s, i, '[')) return false;
        long long q = parseInt(s, i);
        if (!consumeChar(s, i, ',')) return false;
        long long v = parseInt(s, i);
        if (!consumeChar(s, i, ',')) return false;
        long long m = parseInt(s, i);
        if (!consumeChar(s, i, ',')) return false;
        long long l = parseInt(s, i);
        if (!consumeChar(s, i, ']')) return false;

        Item it;
        it.name = key;
        it.q = (int)q;
        it.v = v;
        it.m = m;
        it.l = l;
        items.push_back(it);

        skipWS(s, i);
        if (i < s.size() && s[i] == ',') { i++; continue; }
        if (i < s.size() && s[i] == '}') { i++; break; }
    }
    return true;
}

static inline long long evalSolution(const vector<Item>& items, const vector<int>& cnt, long long& mass, long long& vol) {
    long long val = 0;
    mass = 0;
    vol = 0;
    for (int i = 0; i < (int)items.size(); i++) {
        long long c = cnt[i];
        val += c * items[i].v;
        mass += c * items[i].m;
        vol += c * items[i].l;
    }
    return val;
}

static vector<int> pruneFrontier(const vector<State>& pool, vector<int> idx, int capMU, int capVU) {
    if (idx.empty()) return idx;
    auto cmp = [&](int a, int b) {
        const State& A = pool[a];
        const State& B = pool[b];
        if (A.mU != B.mU) return A.mU < B.mU;
        if (A.vU != B.vU) return A.vU < B.vU;
        return A.val > B.val;
    };
    sort(idx.begin(), idx.end(), cmp);

    // Remove duplicates (mU,vU) keeping highest value
    vector<int> uniq;
    uniq.reserve(idx.size());
    int lastM = INT_MIN, lastV = INT_MIN;
    for (int id : idx) {
        const State& S = pool[id];
        if (S.mU < 0 || S.vU < 0 || S.mU > capMU || S.vU > capVU) continue;
        if (S.mU != lastM || S.vU != lastV) {
            uniq.push_back(id);
            lastM = S.mU;
            lastV = S.vU;
        }
    }
    if (uniq.empty()) return uniq;

    // Prune within equal mass: increasing vol must have increasing value
    vector<int> intra;
    intra.reserve(uniq.size());
    size_t p = 0;
    while (p < uniq.size()) {
        int m = pool[uniq[p]].mU;
        long long bestVal = -1;
        while (p < uniq.size() && pool[uniq[p]].mU == m) {
            int id = uniq[p++];
            long long v = pool[id].val;
            if (v > bestVal) {
                intra.push_back(id);
                bestVal = v;
            }
        }
    }
    if (intra.empty()) return intra;

    // Cross-mass dominance pruning using BIT over volume prefix max(value)
    vector<int> vols;
    vols.reserve(intra.size());
    for (int id : intra) vols.push_back(pool[id].vU);
    sort(vols.begin(), vols.end());
    vols.erase(unique(vols.begin(), vols.end()), vols.end());
    FenwickMax bit((int)vols.size());

    vector<int> kept;
    kept.reserve(intra.size());
    p = 0;
    while (p < intra.size()) {
        int m = pool[intra[p]].mU;
        size_t start = p;
        while (p < intra.size() && pool[intra[p]].mU == m) p++;

        // Query (domination by strictly smaller mass) - OK due to within-mass pruning already done
        vector<int> groupKept;
        groupKept.reserve(p - start);
        for (size_t t = start; t < p; t++) {
            int id = intra[t];
            int volU = pool[id].vU;
            long long val = pool[id].val;
            int pos = (int)(lower_bound(vols.begin(), vols.end(), volU) - vols.begin()) + 1;
            if (bit.query(pos) >= val) continue;
            groupKept.push_back(id);
            kept.push_back(id);
        }
        // Update after group
        for (int id : groupKept) {
            int volU = pool[id].vU;
            long long val = pool[id].val;
            int pos = (int)(lower_bound(vols.begin(), vols.end(), volU) - vols.begin()) + 1;
            bit.update(pos, val);
        }
    }

    // Optional thinning if too large
    const int HARD_MAX = 150000;
    const int BUCKET_MAX = 70000;
    if ((int)kept.size() > HARD_MAX) {
        int MB = 210, VB = 260;
        int massStep = max(1, capMU / MB + 1);
        int volStep  = max(1, capVU / VB + 1);
        vector<int> bestIdx(MB * VB, -1);
        vector<long long> bestVal(MB * VB, -1);
        for (int id : kept) {
            const State& S = pool[id];
            int mb = min(MB - 1, S.mU / massStep);
            int vb = min(VB - 1, S.vU / volStep);
            int pos = mb * VB + vb;
            if (S.val > bestVal[pos]) {
                bestVal[pos] = S.val;
                bestIdx[pos] = id;
            }
        }
        vector<int> thinned;
        thinned.reserve(MB * VB);
        for (int id : bestIdx) if (id != -1) thinned.push_back(id);
        if ((int)thinned.size() > BUCKET_MAX) {
            sort(thinned.begin(), thinned.end(), [&](int a, int b) { return pool[a].val > pool[b].val; });
            thinned.resize(BUCKET_MAX);
        }
        return thinned;
    }
    return kept;
}

static vector<int> solveDPScaled(const vector<Item>& items, long long massUnit, long long volUnit, int orderMode) {
    int n = (int)items.size();
    int capMU = (int)(CAP_M / massUnit);
    int capVU = (int)(CAP_V / volUnit);

    vector<Bundle> bundles;
    bundles.reserve(200);

    for (int i = 0; i < n; i++) {
        int rem = items[i].q;
        int p = 1;
        while (rem > 0) {
            int take = min(p, rem);
            rem -= take;
            p <<= 1;
            long long mTot = (long long)take * items[i].m;
            long long vTot = (long long)take * items[i].l;
            int mU = (int)((mTot + massUnit - 1) / massUnit);
            int vU = (int)((vTot + volUnit - 1) / volUnit);
            if (mU <= capMU && vU <= capVU) {
                Bundle b;
                b.type = i;
                b.cnt = take;
                b.mU = mU;
                b.vU = vU;
                b.val = (long long)take * items[i].v;
                bundles.push_back(b);
            }
        }
    }

    auto densityKey = [&](const Bundle& b) -> long double {
        long double cost = (long double)b.mU / max(1, capMU) + (long double)b.vU / max(1, capVU);
        if (cost <= 0) cost = 1e-18L;
        return (long double)b.val / cost;
    };

    if (orderMode == 1) {
        sort(bundles.begin(), bundles.end(), [&](const Bundle& a, const Bundle& b) {
            long double da = densityKey(a), db = densityKey(b);
            if (da != db) return da > db;
            return a.val > b.val;
        });
    } else if (orderMode == 2) {
        sort(bundles.begin(), bundles.end(), [&](const Bundle& a, const Bundle& b) {
            if (a.val != b.val) return a.val > b.val;
            if (a.mU != b.mU) return a.mU < b.mU;
            return a.vU < b.vU;
        });
    }

    vector<State> pool;
    pool.reserve(200000);
    pool.push_back(State{0, 0, 0, -1, -1});
    vector<int> frontier;
    frontier.reserve(1000);
    frontier.push_back(0);

    for (int bi = 0; bi < (int)bundles.size(); bi++) {
        const Bundle& b = bundles[bi];
        vector<int> candidates;
        candidates.reserve(frontier.size() * 2 + 4);
        for (int id : frontier) candidates.push_back(id);

        for (int id : frontier) {
            const State& s = pool[id];
            int nm = s.mU + b.mU;
            int nv = s.vU + b.vU;
            if (nm > capMU || nv > capVU) continue;
            State ns;
            ns.mU = nm;
            ns.vU = nv;
            ns.val = s.val + b.val;
            ns.prev = id;
            ns.bundle = bi;
            pool.push_back(ns);
            candidates.push_back((int)pool.size() - 1);
        }

        frontier = pruneFrontier(pool, std::move(candidates), capMU, capVU);
        if (frontier.empty()) frontier.push_back(0);
    }

    // Best final state
    int bestId = frontier[0];
    for (int id : frontier) if (pool[id].val > pool[bestId].val) bestId = id;

    vector<int> cnt(n, 0);
    int cur = bestId;
    while (cur > 0) {
        int bi = pool[cur].bundle;
        if (bi >= 0) cnt[bundles[bi].type] += bundles[bi].cnt;
        cur = pool[cur].prev;
        if (cur < 0) break;
    }
    // Clamp to bounds just in case
    for (int i = 0; i < n; i++) cnt[i] = min(cnt[i], items[i].q);
    return cnt;
}

static void greedyFill(const vector<Item>& items, vector<int>& cnt) {
    int n = (int)items.size();
    long long usedM = 0, usedV = 0;
    for (int i = 0; i < n; i++) {
        usedM += (long long)cnt[i] * items[i].m;
        usedV += (long long)cnt[i] * items[i].l;
    }

    while (true) {
        int best = -1;
        long double bestScore = -1;
        for (int i = 0; i < n; i++) {
            if (cnt[i] >= items[i].q) continue;
            if (usedM + items[i].m > CAP_M) continue;
            if (usedV + items[i].l > CAP_V) continue;
            long double cost = (long double)items[i].m / (long double)CAP_M + (long double)items[i].l / (long double)CAP_V;
            if (cost <= 0) cost = 1e-18L;
            long double score = (long double)items[i].v / cost;
            if (score > bestScore) {
                bestScore = score;
                best = i;
            }
        }
        if (best < 0) break;
        long long rem = items[best].q - cnt[best];
        long long kM = (CAP_M - usedM) / items[best].m;
        long long kV = (CAP_V - usedV) / items[best].l;
        long long add = min<long long>(rem, min(kM, kV));
        if (add <= 0) break;
        cnt[best] += (int)add;
        usedM += add * items[best].m;
        usedV += add * items[best].l;
    }
}

static void localImprove(const vector<Item>& items, vector<int>& cnt) {
    int n = (int)items.size();
    long long usedM = 0, usedV = 0;
    long long usedVal = 0;
    for (int i = 0; i < n; i++) {
        usedM += (long long)cnt[i] * items[i].m;
        usedV += (long long)cnt[i] * items[i].l;
        usedVal += (long long)cnt[i] * items[i].v;
    }

    auto applyGreedy = [&]() {
        greedyFill(items, cnt);
        usedM = usedV = usedVal = 0;
        for (int i = 0; i < n; i++) {
            usedM += (long long)cnt[i] * items[i].m;
            usedV += (long long)cnt[i] * items[i].l;
            usedVal += (long long)cnt[i] * items[i].v;
        }
    };

    applyGreedy();

    auto candidateRemovals = [&](int c) {
        vector<int> r;
        int lim = min(c, 20);
        for (int x = 1; x <= lim; x++) r.push_back(x);
        for (int x = 1; x < c; x <<= 1) r.push_back(min(c, x));
        r.push_back(c);
        sort(r.begin(), r.end());
        r.erase(unique(r.begin(), r.end()), r.end());
        return r;
    };

    for (int iter = 0; iter < 120; iter++) {
        long long bestDelta = 0;
        int bestI = -1, bestJ = -1, bestR = 0, bestA = 0;

        for (int i = 0; i < n; i++) {
            if (cnt[i] <= 0) continue;
            vector<int> rs = candidateRemovals(cnt[i]);
            for (int r : rs) {
                long long newUsedM = usedM - (long long)r * items[i].m;
                long long newUsedV = usedV - (long long)r * items[i].l;
                if (newUsedM < 0 || newUsedV < 0) continue;

                long long availM = CAP_M - newUsedM;
                long long availV = CAP_V - newUsedV;

                for (int j = 0; j < n; j++) {
                    long long remJ = items[j].q - cnt[j];
                    if (j == i) remJ += r;
                    if (remJ <= 0) continue;
                    if (items[j].m > availM || items[j].l > availV) continue;
                    long long maxA = min(remJ, min(availM / items[j].m, availV / items[j].l));
                    if (maxA <= 0) continue;

                    long long delta = maxA * items[j].v - (long long)r * items[i].v;
                    if (delta > bestDelta) {
                        bestDelta = delta;
                        bestI = i; bestJ = j;
                        bestR = r;
                        bestA = (int)maxA;
                    }
                }
            }
        }

        if (bestDelta <= 0) break;

        // Apply best move
        cnt[bestI] -= bestR;
        cnt[bestJ] += bestA;
        // Clamp
        for (int i = 0; i < n; i++) cnt[i] = max(0, min(cnt[i], items[i].q));

        usedM = usedV = usedVal = 0;
        for (int i = 0; i < n; i++) {
            usedM += (long long)cnt[i] * items[i].m;
            usedV += (long long)cnt[i] * items[i].l;
            usedVal += (long long)cnt[i] * items[i].v;
        }
        if (usedM > CAP_M || usedV > CAP_V) {
            // Repair with greedy from scratch if something went wrong (shouldn't happen)
            for (int i = 0; i < n; i++) cnt[i] = 0;
            usedM = usedV = usedVal = 0;
        }
        applyGreedy();
    }
}

static vector<int> greedyLambda(const vector<Item>& items, long double lambda) {
    int n = (int)items.size();
    vector<int> cnt(n, 0);
    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 0);
    auto dens = [&](int i) -> long double {
        long double cost = (long double)items[i].m / (long double)CAP_M + lambda * (long double)items[i].l / (long double)CAP_V;
        if (cost <= 0) cost = 1e-18L;
        return (long double)items[i].v / cost;
    };
    sort(ord.begin(), ord.end(), [&](int a, int b) {
        long double da = dens(a), db = dens(b);
        if (da != db) return da > db;
        return items[a].v > items[b].v;
    });

    long long usedM = 0, usedV = 0;
    for (int i : ord) {
        if (items[i].m > CAP_M || items[i].l > CAP_V) continue;
        long long k = min<long long>(items[i].q,
            min((CAP_M - usedM) / items[i].m, (CAP_V - usedV) / items[i].l));
        if (k <= 0) continue;
        cnt[i] = (int)k;
        usedM += k * items[i].m;
        usedV += k * items[i].l;
    }
    greedyFill(items, cnt);
    return cnt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    vector<Item> items;
    if (!parseInputJSON(input, items)) {
        // Fallback: output empty object
        cout << "{}\n";
        return 0;
    }

    int n = (int)items.size();
    vector<Solution> candidates;

    // DP candidates with multiple scales and orders
    vector<pair<long long,long long>> scales = {{1000,1000}, {2000,2000}, {500,500}, {5000,5000}};
    for (auto [mu, vu] : scales) {
        if (CAP_M % mu != 0 || CAP_V % vu != 0) continue;
        for (int orderMode = 0; orderMode <= 2; orderMode++) {
            vector<int> c = solveDPScaled(items, mu, vu, orderMode);
            Solution sol;
            sol.cnt = std::move(c);
            sol.value = evalSolution(items, sol.cnt, sol.mass, sol.vol);
            if (sol.mass <= CAP_M && sol.vol <= CAP_V) candidates.push_back(sol);
        }
    }

    // Greedy candidates with different lambdas
    vector<long double> lambdas = {0.0L, 0.15L, 0.3L, 0.6L, 1.0L, 1.7L, 3.0L, 6.0L};
    for (auto lam : lambdas) {
        vector<int> c = greedyLambda(items, lam);
        Solution sol;
        sol.cnt = std::move(c);
        sol.value = evalSolution(items, sol.cnt, sol.mass, sol.vol);
        if (sol.mass <= CAP_M && sol.vol <= CAP_V) candidates.push_back(sol);
    }

    // Sort and improve top few
    sort(candidates.begin(), candidates.end(), [&](const Solution& a, const Solution& b) {
        return a.value > b.value;
    });

    int improveCount = min<int>((int)candidates.size(), 5);
    Solution best;
    best.value = -1;
    best.cnt.assign(n, 0);

    for (int idx = 0; idx < (int)candidates.size(); idx++) {
        Solution sol = candidates[idx];
        if (idx < improveCount) {
            localImprove(items, sol.cnt);
            sol.value = evalSolution(items, sol.cnt, sol.mass, sol.vol);
        }
        if (sol.mass <= CAP_M && sol.vol <= CAP_V && sol.value > best.value) {
            best = std::move(sol);
        }
    }

    // Final safety clamp and feasibility fix if needed
    for (int i = 0; i < n; i++) best.cnt[i] = max(0, min(best.cnt[i], items[i].q));
    long long mCheck = 0, vCheck = 0;
    long long valCheck = evalSolution(items, best.cnt, mCheck, vCheck);
    if (mCheck > CAP_M || vCheck > CAP_V) {
        // fallback to greedy
        best.cnt = greedyLambda(items, 1.0L);
        for (int i = 0; i < n; i++) best.cnt[i] = max(0, min(best.cnt[i], items[i].q));
    }

    // Output JSON with same keys as input (preserve order in items vector)
    cout << "{";
    for (int i = 0; i < n; i++) {
        if (i) cout << ",";
        cout << "\n" << " \"" << items[i].name << "\": " << best.cnt[i];
    }
    if (n) cout << "\n";
    cout << "}\n";
    return 0;
}