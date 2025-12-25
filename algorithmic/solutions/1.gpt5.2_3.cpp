#include <bits/stdc++.h>
using namespace std;

static const long long CAP_M = 20LL * 1000 * 1000;  // mg
static const long long CAP_L = 25LL * 1000 * 1000;  // uL

struct Item {
    string name;
    int q;
    long long v, m, l;
};

struct Solution {
    vector<int> cnt;
    long long usedM = 0, usedL = 0;
    long long value = 0;
};

struct Parser {
    string s;
    size_t p = 0;

    explicit Parser(string in) : s(std::move(in)) {}

    void skipws() {
        while (p < s.size() && (unsigned char)s[p] <= ' ') p++;
    }

    bool consume(char c) {
        skipws();
        if (p < s.size() && s[p] == c) { p++; return true; }
        return false;
    }

    void expect(char c) {
        skipws();
        if (p >= s.size() || s[p] != c) {
            // minimal fail-fast
            cerr << "Parse error: expected '" << c << "' at " << p << "\n";
            exit(1);
        }
        p++;
    }

    string parseString() {
        skipws();
        expect('"');
        string out;
        while (p < s.size() && s[p] != '"') {
            out.push_back(s[p++]);
        }
        expect('"');
        return out;
    }

    long long parseInt() {
        skipws();
        bool neg = false;
        if (p < s.size() && s[p] == '-') { neg = true; p++; }
        if (p >= s.size() || !isdigit((unsigned char)s[p])) {
            cerr << "Parse error: expected int at " << p << "\n";
            exit(1);
        }
        long long x = 0;
        while (p < s.size() && isdigit((unsigned char)s[p])) {
            x = x * 10 + (s[p] - '0');
            p++;
        }
        return neg ? -x : x;
    }

    array<long long,4> parseArray4() {
        skipws();
        expect('[');
        array<long long,4> a{};
        for (int i = 0; i < 4; i++) {
            a[i] = parseInt();
            skipws();
            if (i < 3) expect(',');
        }
        skipws();
        expect(']');
        return a;
    }

    vector<Item> parseObjectItemsInOrder() {
        skipws();
        expect('{');
        vector<Item> items;
        skipws();
        if (consume('}')) return items;
        while (true) {
            string key = parseString();
            skipws();
            expect(':');
            auto arr = parseArray4();
            Item it;
            it.name = key;
            it.q = (int)arr[0];
            it.v = arr[1];
            it.m = arr[2];
            it.l = arr[3];
            items.push_back(it);

            skipws();
            if (consume('}')) break;
            expect(',');
        }
        return items;
    }
};

static inline long long clampLL(long long x, long long lo, long long hi) {
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

static inline long long ceil_div(long long a, long long b) {
    if (a <= 0) return 0;
    return (a + b - 1) / b;
}

static inline long double densityWeighted(const Item& it, long double beta) {
    long double dm = (long double)it.m / (long double)CAP_M;
    long double dl = (long double)it.l / (long double)CAP_L;
    long double denom = beta * dm + (1.0L - beta) * dl;
    if (denom <= 0) denom = 1e-18L;
    return (long double)it.v / denom;
}

static void recompute(Solution& sol, const vector<Item>& items) {
    sol.usedM = sol.usedL = 0;
    __int128 val = 0;
    for (int i = 0; i < (int)items.size(); i++) {
        long long c = sol.cnt[i];
        sol.usedM += c * items[i].m;
        sol.usedL += c * items[i].l;
        val += (__int128)c * (__int128)items[i].v;
    }
    sol.value = (long long)val;
}

static void fillBest(Solution& sol, const vector<Item>& items, const vector<int>& addOrder) {
    for (int idx : addOrder) {
        const auto& it = items[idx];
        int remQ = it.q - sol.cnt[idx];
        if (remQ <= 0) continue;
        long long canM = (CAP_M - sol.usedM) / it.m;
        long long canL = (CAP_L - sol.usedL) / it.l;
        long long add = min<long long>(remQ, min(canM, canL));
        if (add <= 0) continue;
        sol.cnt[idx] += (int)add;
        sol.usedM += add * it.m;
        sol.usedL += add * it.l;
        sol.value += add * it.v;
    }
}

static void localImproveWeighted(Solution& sol, const vector<Item>& items, long double beta) {
    int n = (int)items.size();
    vector<int> idxs(n);
    iota(idxs.begin(), idxs.end(), 0);

    vector<long double> den(n);
    for (int i = 0; i < n; i++) den[i] = densityWeighted(items[i], beta);

    vector<int> addOrder = idxs;
    sort(addOrder.begin(), addOrder.end(), [&](int a, int b){
        if (den[a] != den[b]) return den[a] > den[b];
        return items[a].v > items[b].v;
    });

    vector<int> removeOrder = idxs;
    sort(removeOrder.begin(), removeOrder.end(), [&](int a, int b){
        if (den[a] != den[b]) return den[a] < den[b];
        return items[a].v < items[b].v;
    });

    // Ensure feasibility (should already be feasible in construction)
    if (sol.usedM > CAP_M || sol.usedL > CAP_L) {
        // Greedy removal until feasible
        for (int j : removeOrder) {
            if (sol.usedM <= CAP_M && sol.usedL <= CAP_L) break;
            if (sol.cnt[j] <= 0) continue;
            const auto& it = items[j];
            long long overM = max(0LL, sol.usedM - CAP_M);
            long long overL = max(0LL, sol.usedL - CAP_L);
            long long needM = ceil_div(overM, it.m);
            long long needL = ceil_div(overL, it.l);
            long long rem = max(needM, needL);
            rem = min<long long>(rem, sol.cnt[j]);
            if (rem <= 0) continue;
            sol.cnt[j] -= (int)rem;
            sol.usedM -= rem * it.m;
            sol.usedL -= rem * it.l;
            sol.value -= rem * it.v;
        }
    }

    const int MAX_STEPS = 2500;
    vector<long long> bestRem(n), remTmp(n);

    for (int step = 0; step < MAX_STEPS; step++) {
        fillBest(sol, items, addOrder);

        long long freeM = CAP_M - sol.usedM;
        long long freeL = CAP_L - sol.usedL;

        long long bestGain = 0;
        int bestAdd = -1;
        fill(bestRem.begin(), bestRem.end(), 0);

        for (int i = 0; i < n; i++) {
            const auto& addIt = items[i];
            if (sol.cnt[i] >= addIt.q) continue;

            long long reqM = max(0LL, addIt.m - freeM);
            long long reqL = max(0LL, addIt.l - freeL);

            long long gain = 0;
            fill(remTmp.begin(), remTmp.end(), 0);

            if (reqM == 0 && reqL == 0) {
                gain = addIt.v;
            } else {
                long long defM = reqM;
                long long defL = reqL;
                __int128 lost = 0;

                for (int j : removeOrder) {
                    if (j == i) continue;
                    int have = sol.cnt[j];
                    if (have <= 0) continue;
                    const auto& remIt = items[j];

                    long long needM = ceil_div(defM, remIt.m);
                    long long needL = ceil_div(defL, remIt.l);
                    long long x = max(needM, needL);
                    if (x <= 0) break;
                    x = min<long long>(x, have);
                    if (x <= 0) continue;

                    remTmp[j] = x;
                    lost += (__int128)x * (__int128)remIt.v;
                    defM -= x * remIt.m;
                    defL -= x * remIt.l;
                    if (defM <= 0 && defL <= 0) break;
                }
                if (defM > 0 || defL > 0) continue;
                __int128 net = (__int128)addIt.v - lost;
                if (net <= 0) continue;
                gain = (long long)net;
            }

            if (gain > bestGain || (gain == bestGain && bestAdd != -1 && items[i].v > items[bestAdd].v)) {
                bestGain = gain;
                bestAdd = i;
                bestRem = remTmp;
            }
        }

        if (bestGain <= 0 || bestAdd < 0) break;

        // Apply best move: remove first, then add
        for (int j = 0; j < n; j++) {
            long long r = bestRem[j];
            if (r <= 0) continue;
            const auto& it = items[j];
            if (r > sol.cnt[j]) r = sol.cnt[j];
            sol.cnt[j] -= (int)r;
            sol.usedM -= r * it.m;
            sol.usedL -= r * it.l;
            sol.value -= r * it.v;
        }
        {
            const auto& it = items[bestAdd];
            if (sol.cnt[bestAdd] < it.q &&
                sol.usedM + it.m <= CAP_M &&
                sol.usedL + it.l <= CAP_L) {
                sol.cnt[bestAdd] += 1;
                sol.usedM += it.m;
                sol.usedL += it.l;
                sol.value += it.v;
            } else {
                // If somehow can't add, stop
                break;
            }
        }
    }

    // Final fill
    fillBest(sol, items, addOrder);
}

static Solution greedyByAlpha(const vector<Item>& items, long double alpha) {
    int n = (int)items.size();
    vector<int> idxs(n);
    iota(idxs.begin(), idxs.end(), 0);

    vector<long double> score(n);
    for (int i = 0; i < n; i++) {
        long double dm = (long double)items[i].m / (long double)CAP_M;
        long double dl = (long double)items[i].l / (long double)CAP_L;
        long double denom = alpha * dm + (1.0L - alpha) * dl;
        if (denom <= 0) denom = 1e-18L;
        score[i] = (long double)items[i].v / denom;
    }

    sort(idxs.begin(), idxs.end(), [&](int a, int b){
        if (score[a] != score[b]) return score[a] > score[b];
        return items[a].v > items[b].v;
    });

    Solution sol;
    sol.cnt.assign(n, 0);
    for (int idx : idxs) {
        const auto& it = items[idx];
        long long canM = (CAP_M - sol.usedM) / it.m;
        long long canL = (CAP_L - sol.usedL) / it.l;
        long long add = min<long long>(it.q, min(canM, canL));
        if (add <= 0) continue;
        sol.cnt[idx] = (int)add;
        sol.usedM += add * it.m;
        sol.usedL += add * it.l;
        sol.value += add * it.v;
    }
    return sol;
}

static void tryCandidate(const vector<Item>& items, Solution sol, Solution& best) {
    // Ensure internal fields correct
    recompute(sol, items);
    if (sol.usedM > CAP_M || sol.usedL > CAP_L) return;

    static const long double betas[] = {0.15L, 0.35L, 0.5L, 0.65L, 0.85L};
    for (long double beta : betas) {
        Solution t = sol;
        localImproveWeighted(t, items, beta);
        if (t.usedM <= CAP_M && t.usedL <= CAP_L && t.value > best.value) best = std::move(t);
    }
    if (sol.value > best.value) best = std::move(sol);
}

struct HeapSol {
    long long value;
    vector<int> cnt;
    bool operator<(const HeapSol& other) const { return value > other.value; } // for min-heap by value
};

static void enumerateSubset(const vector<Item>& items, const vector<int>& subset, int T, vector<Solution>& out) {
    int n = (int)items.size();
    vector<int> baseCnt(n, 0);

    // Precompute add order for beta=0.5 for fast fill
    vector<int> idxs(n);
    iota(idxs.begin(), idxs.end(), 0);
    vector<long double> den(n);
    for (int i = 0; i < n; i++) den[i] = densityWeighted(items[i], 0.5L);
    sort(idxs.begin(), idxs.end(), [&](int a, int b){
        if (den[a] != den[b]) return den[a] > den[b];
        return items[a].v > items[b].v;
    });
    vector<int> addOrder = idxs;

    priority_queue<HeapSol> pq; // min-heap by value (because operator< reversed)

    function<void(int, long long, long long, long long)> dfs = [&](int pos, long long usedM, long long usedL, long long val) {
        if (pos == (int)subset.size()) {
            Solution sol;
            sol.cnt = baseCnt;
            sol.usedM = usedM;
            sol.usedL = usedL;
            sol.value = val;
            fillBest(sol, items, addOrder);

            HeapSol hs{sol.value, sol.cnt};
            if ((int)pq.size() < T) {
                pq.push(std::move(hs));
            } else if (hs.value > pq.top().value) {
                pq.pop();
                pq.push(std::move(hs));
            }
            return;
        }

        int idx = subset[pos];
        const auto& it = items[idx];
        int maxFeas = min(it.q, (int)min(CAP_M / it.m, CAP_L / it.l));
        // Further tightened by remaining capacity
        maxFeas = min<long long>(maxFeas, min((CAP_M - usedM) / it.m, (CAP_L - usedL) / it.l));
        for (int c = 0; c <= maxFeas; c++) {
            long long nm = usedM + 1LL * c * it.m;
            long long nl = usedL + 1LL * c * it.l;
            if (nm > CAP_M || nl > CAP_L) break;
            long long nv = val + 1LL * c * it.v;
            baseCnt[idx] = c;
            dfs(pos + 1, nm, nl, nv);
        }
        baseCnt[idx] = 0;
    };

    dfs(0, 0, 0, 0);

    out.clear();
    out.reserve(pq.size());
    while (!pq.empty()) {
        auto hs = pq.top(); pq.pop();
        Solution sol;
        sol.cnt = std::move(hs.cnt);
        recompute(sol, items);
        out.push_back(std::move(sol));
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    Parser parser(input);
    vector<Item> items = parser.parseObjectItemsInOrder();
    int n = (int)items.size();

    Solution best;
    best.cnt.assign(n, 0);
    best.usedM = best.usedL = best.value = 0;

    // Basic candidates
    {
        Solution zero;
        zero.cnt.assign(n, 0);
        tryCandidate(items, zero, best);
    }

    // Greedy by a variety of alphas
    vector<long double> alphas = {0.0L, 1.0L, 0.5L, 0.25L, 0.75L, 0.1L, 0.9L, 0.33L, 0.67L};
    {
        std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
        uniform_real_distribution<long double> dist(0.0L, 1.0L);
        for (int i = 0; i < 50; i++) alphas.push_back(dist(rng));
    }
    for (long double a : alphas) {
        Solution sol = greedyByAlpha(items, a);
        tryCandidate(items, sol, best);
    }

    // Candidate based on single constraints
    {
        // mass-only (alpha=1) and volume-only (alpha=0) already included; try extreme skews
        vector<long double> extra = {0.02L, 0.98L, 0.05L, 0.95L};
        for (auto a : extra) {
            Solution sol = greedyByAlpha(items, a);
            tryCandidate(items, sol, best);
        }
    }

    // Enumeration on a small subset with low maxFeasible
    vector<int> idxs(n);
    iota(idxs.begin(), idxs.end(), 0);
    vector<int> maxFeas(n);
    for (int i = 0; i < n; i++) {
        maxFeas[i] = min(items[i].q, (int)min(CAP_M / items[i].m, CAP_L / items[i].l));
    }
    sort(idxs.begin(), idxs.end(), [&](int a, int b){
        if (maxFeas[a] != maxFeas[b]) return maxFeas[a] < maxFeas[b];
        return items[a].v > items[b].v;
    });

    vector<int> subset;
    long long prod = 1;
    const long long LEAF_LIMIT = 30000;
    for (int idx : idxs) {
        long long next = prod * (long long)(maxFeas[idx] + 1);
        if ((int)subset.size() >= 5) break;
        if (next > LEAF_LIMIT) continue;
        subset.push_back(idx);
        prod = next;
        if (prod >= LEAF_LIMIT) break;
    }

    if (!subset.empty()) {
        vector<Solution> leafSols;
        enumerateSubset(items, subset, 60, leafSols);
        for (auto &sol : leafSols) tryCandidate(items, sol, best);
    }

    // Random perturbations around best
    {
        std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ 0x9e3779b97f4a7c15ULL);
        uniform_int_distribution<int> typeDist(0, max(0, n-1));

        for (int it = 0; it < 220; it++) {
            Solution s = best;
            int shakes = 2 + (int)(rng() % 4);
            for (int k = 0; k < shakes; k++) {
                int i = typeDist(rng);
                if (s.cnt[i] <= 0) continue;
                int mx = max(1, s.cnt[i] / 2);
                int rem = 1 + (int)(rng() % (unsigned long long)mx);
                rem = min(rem, s.cnt[i]);
                s.cnt[i] -= rem;
            }
            recompute(s, items);
            if (s.usedM > CAP_M || s.usedL > CAP_L) continue;
            tryCandidate(items, s, best);
        }
    }

    // Output JSON
    cout << "{\n";
    for (int i = 0; i < n; i++) {
        cout << " \"" << items[i].name << "\": " << best.cnt[i];
        if (i + 1 < n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";
    return 0;
}