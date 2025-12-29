#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    int q;
    long long v, m, l;
};

struct Solution {
    vector<long long> x;
    long long mass = 0, vol = 0, val = 0;
};

static const long long CAP_M = 20LL * 1000000LL;
static const long long CAP_L = 25LL * 1000000LL;

struct Parser {
    string s;
    size_t i = 0;

    explicit Parser(string in) : s(std::move(in)), i(0) {}

    void skipWs() {
        while (i < s.size() && (s[i] == ' ' || s[i] == '\n' || s[i] == '\r' || s[i] == '\t')) i++;
    }

    void expect(char c) {
        skipWs();
        if (i >= s.size() || s[i] != c) {
            // invalid input, but we assume valid per problem statement
            return;
        }
        i++;
    }

    string parseString() {
        skipWs();
        expect('"');
        string out;
        while (i < s.size() && s[i] != '"') {
            out.push_back(s[i]);
            i++;
        }
        expect('"');
        return out;
    }

    long long parseInt() {
        skipWs();
        long long sign = 1;
        if (i < s.size() && s[i] == '-') { sign = -1; i++; }
        long long x = 0;
        while (i < s.size() && isdigit((unsigned char)s[i])) {
            x = x * 10 + (s[i] - '0');
            i++;
        }
        return x * sign;
    }
};

static inline long long clamp_ll(long long x, long long lo, long long hi) {
    return max(lo, min(hi, x));
}

static inline long double densityNormSum(const Item& it, long double alpha) {
    long double dm = (long double)it.m / (long double)CAP_M;
    long double dl = (long double)it.l / (long double)CAP_L;
    long double denom = alpha * dm + (1.0L - alpha) * dl;
    if (denom <= 0) return 0;
    return (long double)it.v / denom;
}

static inline long double densityNormMax(const Item& it) {
    long double dm = (long double)it.m / (long double)CAP_M;
    long double dl = (long double)it.l / (long double)CAP_L;
    long double denom = max(dm, dl);
    if (denom <= 0) return 0;
    return (long double)it.v / denom;
}

static inline long double densitySumRaw(const Item& it, long double lambda) {
    long double denom = (long double)it.m + lambda * (long double)it.l;
    if (denom <= 0) return 0;
    return (long double)it.v / denom;
}

static Solution evalSolution(const vector<Item>& items, const vector<long long>& x) {
    Solution sol;
    sol.x = x;
    sol.mass = sol.vol = sol.val = 0;
    for (size_t k = 0; k < items.size(); k++) {
        sol.mass += items[k].m * sol.x[k];
        sol.vol  += items[k].l * sol.x[k];
        sol.val  += items[k].v * sol.x[k];
    }
    return sol;
}

static void refillWithOrder(const vector<Item>& items, Solution& sol, const vector<int>& order) {
    for (int idx : order) {
        const auto& it = items[idx];
        if (sol.x[idx] >= it.q) continue;
        long long remM = CAP_M - sol.mass;
        long long remL = CAP_L - sol.vol;
        if (remM <= 0 || remL <= 0) continue;
        long long add = it.q - sol.x[idx];
        add = min(add, remM / it.m);
        add = min(add, remL / it.l);
        if (add <= 0) continue;
        sol.x[idx] += add;
        sol.mass += it.m * add;
        sol.vol  += it.l * add;
        sol.val  += it.v * add;
    }
}

static void greedyFillFromEmpty(const vector<Item>& items, Solution& sol, const vector<int>& order) {
    sol.x.assign(items.size(), 0);
    sol.mass = sol.vol = sol.val = 0;
    refillWithOrder(items, sol, order);
}

static void repairFeasible(const vector<Item>& items, Solution& sol) {
    if (sol.mass <= CAP_M && sol.vol <= CAP_L) return;

    int n = (int)items.size();
    vector<int> idxs(n);
    iota(idxs.begin(), idxs.end(), 0);

    auto dens = [&](int i) -> long double {
        return densityNormSum(items[i], 0.5L);
    };

    // Remove lowest density items in bulk until feasible.
    for (int step = 0; step < 1000 && (sol.mass > CAP_M || sol.vol > CAP_L); step++) {
        int best = -1;
        long double bestD = 1e300L;
        for (int i = 0; i < n; i++) {
            if (sol.x[i] <= 0) continue;
            long double d = dens(i);
            if (d < bestD) { bestD = d; best = i; }
        }
        if (best < 0) break;

        long long overM = max(0LL, sol.mass - CAP_M);
        long long overL = max(0LL, sol.vol - CAP_L);
        const auto& it = items[best];

        long long need = 1;
        if (overM > 0) need = max(need, (overM + it.m - 1) / it.m);
        if (overL > 0) need = max(need, (overL + it.l - 1) / it.l);
        need = min(need, sol.x[best]);
        if (need <= 0) need = 1;

        sol.x[best] -= need;
        sol.mass -= it.m * need;
        sol.vol  -= it.l * need;
        sol.val  -= it.v * need;
    }

    // Final safety: remove one by one if still infeasible.
    for (int step = 0; step < 100000 && (sol.mass > CAP_M || sol.vol > CAP_L); step++) {
        int best = -1;
        long double bestD = 1e300L;
        for (int i = 0; i < (int)items.size(); i++) {
            if (sol.x[i] <= 0) continue;
            long double d = densityNormSum(items[i], 0.5L);
            if (d < bestD) { bestD = d; best = i; }
        }
        if (best < 0) break;
        sol.x[best]--;
        sol.mass -= items[best].m;
        sol.vol  -= items[best].l;
        sol.val  -= items[best].v;
    }

    if (sol.mass < 0) sol.mass = 0;
    if (sol.vol < 0) sol.vol = 0;
    if (sol.val < 0) sol.val = 0;
}

static bool pairOptimizeExact(const vector<Item>& items, Solution& sol, int i, int j) {
    if (i == j) return false;
    const auto& A = items[i];
    const auto& B = items[j];

    long long xi = sol.x[i], xj = sol.x[j];
    long long mass_others = sol.mass - A.m * xi - B.m * xj;
    long long vol_others  = sol.vol  - A.l * xi - B.l * xj;
    long long val_others  = sol.val  - A.v * xi - B.v * xj;

    long long Mrem = CAP_M - mass_others;
    long long Lrem = CAP_L - vol_others;
    if (Mrem < 0 || Lrem < 0) return false;

    long long aUpper = min<long long>(A.q, min(Mrem / A.m, Lrem / A.l));
    long long bUpper = min<long long>(B.q, min(Mrem / B.m, Lrem / B.l));

    long long curPairVal = A.v * xi + B.v * xj;
    long long curPairMass = A.m * xi + B.m * xj;
    long long curPairVol  = A.l * xi + B.l * xj;

    long long bestA = xi, bestB = xj;
    long long bestPairVal = curPairVal;
    long long bestPairUsed = curPairMass + curPairVol;

    auto consider = [&](long long a, long long b) {
        if (a < 0 || b < 0) return;
        if (a > A.q || b > B.q) return;
        long long mm = A.m * a + B.m * b;
        long long ll = A.l * a + B.l * b;
        if (mm > Mrem || ll > Lrem) return;
        long long vv = A.v * a + B.v * b;
        long long used = mm + ll;
        if (vv > bestPairVal || (vv == bestPairVal && used < bestPairUsed)) {
            bestPairVal = vv;
            bestPairUsed = used;
            bestA = a;
            bestB = b;
        }
    };

    if (aUpper <= bUpper) {
        for (long long a = 0; a <= aUpper; a++) {
            long long Mleft = Mrem - A.m * a;
            long long Lleft = Lrem - A.l * a;
            if (Mleft < 0 || Lleft < 0) break;
            long long b = min<long long>(B.q, min(Mleft / B.m, Lleft / B.l));
            consider(a, b);
        }
    } else {
        for (long long b = 0; b <= bUpper; b++) {
            long long Mleft = Mrem - B.m * b;
            long long Lleft = Lrem - B.l * b;
            if (Mleft < 0 || Lleft < 0) break;
            long long a = min<long long>(A.q, min(Mleft / A.m, Lleft / A.l));
            consider(a, b);
        }
    }

    if (bestA == xi && bestB == xj) return false;

    // Apply
    sol.x[i] = bestA;
    sol.x[j] = bestB;
    sol.mass = mass_others + A.m * bestA + B.m * bestB;
    sol.vol  = vol_others  + A.l * bestA + B.l * bestB;
    sol.val  = val_others  + A.v * bestA + B.v * bestB;

    return true;
}

static void improveSolution(const vector<Item>& items, Solution& sol, const vector<int>& refillOrder, mt19937_64& rng, int maxRounds) {
    repairFeasible(items, sol);
    refillWithOrder(items, sol, refillOrder);
    repairFeasible(items, sol);

    int n = (int)items.size();
    vector<pair<int,int>> pairs;
    pairs.reserve(n*(n-1)/2);
    for (int i = 0; i < n; i++)
        for (int j = i+1; j < n; j++)
            pairs.emplace_back(i,j);

    for (int round = 0; round < maxRounds; round++) {
        bool changed = false;
        shuffle(pairs.begin(), pairs.end(), rng);
        for (auto [i,j] : pairs) {
            changed |= pairOptimizeExact(items, sol, i, j);
        }
        long long oldVal = sol.val;
        long long oldMass = sol.mass, oldVol = sol.vol;
        refillWithOrder(items, sol, refillOrder);
        if (sol.val != oldVal || sol.mass != oldMass || sol.vol != oldVol) changed = true;
        if (!changed) break;
    }
    repairFeasible(items, sol);
}

static vector<int> makeOrder(const vector<Item>& items, function<long double(const Item&)> scoreFn) {
    int n = (int)items.size();
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        long double sa = scoreFn(items[a]);
        long double sb = scoreFn(items[b]);
        if (sa != sb) return sa > sb;
        return items[a].v > items[b].v;
    });
    return order;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input, line;
    while (getline(cin, line)) {
        input += line;
        input.push_back('\n');
    }

    Parser p(input);
    p.skipWs();
    p.expect('{');

    vector<Item> items;
    vector<string> keyOrder;

    while (true) {
        p.skipWs();
        if (p.i < p.s.size() && p.s[p.i] == '}') { p.i++; break; }
        string key = p.parseString();
        keyOrder.push_back(key);
        p.skipWs();
        p.expect(':');
        p.skipWs();
        p.expect('[');
        long long q = p.parseInt();
        p.skipWs(); p.expect(',');
        long long v = p.parseInt();
        p.skipWs(); p.expect(',');
        long long m = p.parseInt();
        p.skipWs(); p.expect(',');
        long long l = p.parseInt();
        p.skipWs();
        p.expect(']');
        items.push_back(Item{key, (int)q, v, m, l});
        p.skipWs();
        if (p.i < p.s.size() && p.s[p.i] == ',') { p.i++; continue; }
        if (p.i < p.s.size() && p.s[p.i] == '}') { p.i++; break; }
    }

    int n = (int)items.size();
    // Safety if input malformed; but statement guarantees exactly 12.
    if (n == 0) {
        cout << "{\n}\n";
        return 0;
    }

    mt19937_64 rng(0xC0FFEE123456789ULL);

    // Precompute a few orders
    vector<vector<int>> orders;
    vector<long double> alphas = {0.0L, 0.2L, 0.4L, 0.5L, 0.6L, 0.8L, 1.0L};
    for (auto a : alphas) {
        orders.push_back(makeOrder(items, [a](const Item& it){ return densityNormSum(it, a); }));
    }
    orders.push_back(makeOrder(items, [](const Item& it){ return densityNormMax(it); }));
    orders.push_back(makeOrder(items, [](const Item& it){
        return (it.m > 0) ? (long double)it.v / (long double)it.m : 0.0L;
    }));
    orders.push_back(makeOrder(items, [](const Item& it){
        return (it.l > 0) ? (long double)it.v / (long double)it.l : 0.0L;
    }));
    orders.push_back(makeOrder(items, [](const Item& it){ return (long double)it.v; }));
    orders.push_back(makeOrder(items, [](const Item& it){
        return (long double)it.v / ( (long double)it.m + (long double)it.l );
    }));
    vector<long double> lambdas = {0.0L, 0.01L, 0.05L, 0.1L, 0.2L, 0.5L, 1.0L, 2.0L, 5.0L, 10.0L};
    for (auto lam : lambdas) {
        orders.push_back(makeOrder(items, [lam](const Item& it){ return densitySumRaw(it, lam); }));
    }

    // Baseline best: try each order
    Solution best;
    best.x.assign(n, 0);
    best.mass = best.vol = best.val = 0;

    for (const auto& ord : orders) {
        Solution sol;
        greedyFillFromEmpty(items, sol, ord);
        improveSolution(items, sol, ord, rng, 4);
        if (sol.val > best.val) best = sol;
    }

    // Randomized multi-start / perturbation
    int ITER = 160;
    for (int t = 0; t < ITER; t++) {
        Solution sol = best;

        if (t % 6 == 0) {
            // start from empty with random order
            vector<int> ord(n);
            iota(ord.begin(), ord.end(), 0);
            shuffle(ord.begin(), ord.end(), rng);
            greedyFillFromEmpty(items, sol, ord);
            improveSolution(items, sol, ord, rng, 3);
        } else {
            // perturb best
            for (int i = 0; i < n; i++) {
                if (sol.x[i] == 0) continue;
                uint64_t r = rng() % 100;
                if (r < 8) sol.x[i] = 0;
                else if (r < 24) sol.x[i] = sol.x[i] / 4;
                else if (r < 48) sol.x[i] = sol.x[i] / 2;
                else if (r < 64) sol.x[i] = (sol.x[i] * 3) / 4;
            }
            sol = evalSolution(items, sol.x);
            repairFeasible(items, sol);

            // choose a random alpha-based order to refill
            long double a = (long double)(rng() % 1000) / 1000.0L;
            auto ord = makeOrder(items, [a](const Item& it){ return densityNormSum(it, a); });
            refillWithOrder(items, sol, ord);
            improveSolution(items, sol, ord, rng, 3);
        }

        if (sol.val > best.val) best = sol;
    }

    // Final repair and slight refill using best normalized order
    auto finalOrd = makeOrder(items, [](const Item& it){ return densityNormSum(it, 0.5L); });
    repairFeasible(items, best);
    refillWithOrder(items, best, finalOrd);
    repairFeasible(items, best);

    // Output JSON with same keys as input in the same order.
    // Build mapping from name to count from items order.
    unordered_map<string, long long> out;
    out.reserve(n * 2);
    for (int i = 0; i < n; i++) out[items[i].name] = best.x[i];

    cout << "{\n";
    for (int k = 0; k < (int)keyOrder.size(); k++) {
        const string& key = keyOrder[k];
        long long cnt = 0;
        auto it = out.find(key);
        if (it != out.end()) cnt = it->second;
        cout << " \"" << key << "\": " << cnt;
        if (k + 1 < (int)keyOrder.size()) cout << ",";
        cout << "\n";
    }
    cout << "}\n";
    return 0;
}