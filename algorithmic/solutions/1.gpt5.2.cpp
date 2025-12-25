#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    int q;
    long long v, m, l;
};

static inline void skip_ws(const string& s, size_t& i) {
    while (i < s.size() && isspace((unsigned char)s[i])) i++;
}

static string parse_string(const string& s, size_t& i) {
    skip_ws(s, i);
    if (i >= s.size() || s[i] != '"') return "";
    i++;
    string out;
    while (i < s.size()) {
        char c = s[i++];
        if (c == '"') break;
        if (c == '\\') { // minimal escape support
            if (i < s.size()) {
                char e = s[i++];
                out.push_back(e);
            }
        } else out.push_back(c);
    }
    return out;
}

static long long parse_int(const string& s, size_t& i) {
    skip_ws(s, i);
    bool neg = false;
    if (i < s.size() && s[i] == '-') { neg = true; i++; }
    long long x = 0;
    while (i < s.size() && isdigit((unsigned char)s[i])) {
        x = x * 10 + (s[i] - '0');
        i++;
    }
    return neg ? -x : x;
}

struct Solution {
    array<int,12> x{};
    long long value = 0;
    long long usedM = 0, usedL = 0;
};

static inline long long compute_value(const vector<Item>& items, const array<int,12>& x) {
    long long val = 0;
    for (int i = 0; i < 12; i++) val += (long long)x[i] * items[i].v;
    return val;
}

static inline pair<long long,long long> compute_used(const vector<Item>& items, const array<int,12>& x) {
    __int128 um = 0, ul = 0;
    for (int i = 0; i < 12; i++) {
        um += (__int128)x[i] * items[i].m;
        ul += (__int128)x[i] * items[i].l;
    }
    return {(long long)um, (long long)ul};
}

static Solution greedy(const vector<Item>& items, long long M, long long L, long double alphaM, long double alphaL) {
    vector<int> idx(12);
    iota(idx.begin(), idx.end(), 0);
    vector<long double> score(12, 0);
    for (int i = 0; i < 12; i++) {
        long double denom = alphaM * (long double)items[i].m + alphaL * (long double)items[i].l;
        if (denom <= 0) score[i] = 0;
        else score[i] = (long double)items[i].v / denom;
    }
    stable_sort(idx.begin(), idx.end(), [&](int a, int b){
        if (score[a] != score[b]) return score[a] > score[b];
        return items[a].v > items[b].v;
    });

    Solution sol;
    long long remM = M, remL = L;
    for (int id : idx) {
        if (items[id].m > remM || items[id].l > remL) continue;
        long long byM = remM / items[id].m;
        long long byL = remL / items[id].l;
        long long take = min<long long>(items[id].q, min(byM, byL));
        sol.x[id] = (int)take;
        remM -= take * items[id].m;
        remL -= take * items[id].l;
        sol.value += take * items[id].v;
        sol.usedM += take * items[id].m;
        sol.usedL += take * items[id].l;
    }
    return sol;
}

struct WeightRun {
    long long p, q; // coefficient k = p/q
    bool volCoeff; // if true: w = m*L*q + l*M*p; else: w = m*L*p + l*M*q
};

struct BeamState {
    array<int,12> x{};
    long long remM = 0, remL = 0;
    long long val = 0;
    long double ub = 0;
};

static long double fractional_bound(
    const vector<Item>& items,
    const vector<int>& order,
    int pos,
    long long remM, long long remL,
    long long M, long long L,
    long long wM1, long long wL1
) {
    __int128 remW128 = (__int128)remM * wM1 + (__int128)remL * wL1;
    long long remW = (remW128 > (__int128)LLONG_MAX ? LLONG_MAX : (long long)remW128);
    long double add = 0.0L;

    for (int k = pos; k < (int)order.size(); k++) {
        int i = order[k];
        long long wi;
        {
            __int128 w128 = (__int128)items[i].m * wM1 + (__int128)items[i].l * wL1;
            if (w128 <= 0) continue;
            wi = (w128 > (__int128)LLONG_MAX ? LLONG_MAX : (long long)w128);
        }
        if (wi <= 0) continue;

        long long capByM = (items[i].m == 0 ? (long long)items[i].q : remM / items[i].m);
        long long capByL = (items[i].l == 0 ? (long long)items[i].q : remL / items[i].l);
        long long avail = min<long long>(items[i].q, min(capByM, capByL));
        if (avail <= 0) continue;
        if (remW <= 0) break;

        long long take = min(avail, remW / wi);
        if (take > 0) {
            add += (long double)take * (long double)items[i].v;
            remW -= take * wi;
            remM -= take * items[i].m;
            remL -= take * items[i].l;
        }
        if (take < avail && remW > 0) {
            // fractional
            add += (long double)remW * ((long double)items[i].v / (long double)wi);
            break;
        }
    }
    return add;
}

static Solution beam_search(
    const vector<Item>& items,
    long long M, long long L,
    const WeightRun& wr,
    int BEAM_W
) {
    long long wM1, wL1;
    if (wr.volCoeff) {
        // w = m*(L*q) + l*(M*p)
        wM1 = L * wr.q;
        wL1 = M * wr.p;
    } else {
        // w = m*(L*p) + l*(M*q)
        wM1 = L * wr.p;
        wL1 = M * wr.q;
    }

    vector<int> order(12);
    iota(order.begin(), order.end(), 0);
    vector<long double> dens(12, 0.0L);
    for (int i = 0; i < 12; i++) {
        __int128 w128 = (__int128)items[i].m * wM1 + (__int128)items[i].l * wL1;
        long double wi = (w128 <= 0 ? 1.0L : (long double)(long long)min<__int128>(w128, (__int128)LLONG_MAX));
        dens[i] = (wi <= 0 ? 0.0L : (long double)items[i].v / wi);
    }
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        if (dens[a] != dens[b]) return dens[a] > dens[b];
        // tie-break: prefer higher absolute value
        if (items[a].v != items[b].v) return items[a].v > items[b].v;
        // then smaller combined consumption
        __int128 wa = (__int128)items[a].m * wM1 + (__int128)items[a].l * wL1;
        __int128 wb = (__int128)items[b].m * wM1 + (__int128)items[b].l * wL1;
        return wa < wb;
    });

    vector<BeamState> beam, nxt;
    beam.reserve(BEAM_W);
    nxt.reserve(BEAM_W * 8);

    BeamState init;
    init.remM = M; init.remL = L; init.val = 0;
    init.ub = (long double)init.val + fractional_bound(items, order, 0, init.remM, init.remL, M, L, wM1, wL1);
    beam.push_back(init);

    auto push_state = [&](vector<BeamState>& vec, const BeamState& st){
        vec.push_back(st);
    };

    for (int pos = 0; pos < 12; pos++) {
        nxt.clear();
        int it = order[pos];
        for (const auto& st : beam) {
            long long remM = st.remM, remL = st.remL;
            long long maxTake = 0;
            if (items[it].m <= remM && items[it].l <= remL) {
                long long byM = remM / items[it].m;
                long long byL = remL / items[it].l;
                maxTake = min<long long>(items[it].q, min(byM, byL));
            }

            vector<int> cands;
            cands.reserve(12);
            cands.push_back(0);
            if (maxTake > 0) {
                cands.push_back((int)maxTake);
                cands.push_back(1);
                cands.push_back((int)min<long long>(2, maxTake));
                cands.push_back((int)min<long long>(3, maxTake));
                cands.push_back((int)(maxTake / 2));
                cands.push_back((int)(maxTake / 3));
                cands.push_back((int)(maxTake * 3 / 4));
                cands.push_back((int)(maxTake * 4 / 5));
                cands.push_back((int)(maxTake / 5));
            }
            sort(cands.begin(), cands.end());
            cands.erase(unique(cands.begin(), cands.end()), cands.end());

            for (int take : cands) {
                if (take < 0) continue;
                if ((long long)take > maxTake) continue;
                BeamState ns = st;
                ns.x[it] = take;
                ns.remM = remM - (long long)take * items[it].m;
                ns.remL = remL - (long long)take * items[it].l;
                ns.val = st.val + (long long)take * items[it].v;
                ns.ub = (long double)ns.val + fractional_bound(items, order, pos+1, ns.remM, ns.remL, M, L, wM1, wL1);
                push_state(nxt, ns);
            }
        }

        // Keep top BEAM_W by (ub, val)
        if ((int)nxt.size() > BEAM_W) {
            nth_element(nxt.begin(), nxt.begin() + BEAM_W, nxt.end(), [](const BeamState& a, const BeamState& b){
                if (a.ub != b.ub) return a.ub > b.ub;
                return a.val > b.val;
            });
            nxt.resize(BEAM_W);
        }
        sort(nxt.begin(), nxt.end(), [](const BeamState& a, const BeamState& b){
            if (a.ub != b.ub) return a.ub > b.ub;
            return a.val > b.val;
        });

        beam.swap(nxt);
    }

    // Choose best by value (all feasible)
    Solution best;
    long long bestV = -1;
    for (const auto& st : beam) {
        if (st.val > bestV) {
            bestV = st.val;
            best.x = st.x;
        }
    }
    best.value = bestV;
    auto used = compute_used(items, best.x);
    best.usedM = used.first;
    best.usedL = used.second;
    return best;
}

static Solution local_improve(
    const vector<Item>& items,
    long long M, long long L,
    Solution sol,
    uint64_t seed,
    int ITER
) {
    // fixed density based on normalized combined weight: w = m*L + l*M
    vector<int> order(12);
    iota(order.begin(), order.end(), 0);
    vector<long double> dens(12, 0.0L);
    for (int i = 0; i < 12; i++) {
        __int128 w = (__int128)items[i].m * L + (__int128)items[i].l * M;
        long double wi = (w <= 0 ? 1.0L : (long double)(long long)min<__int128>(w, (__int128)LLONG_MAX));
        dens[i] = (wi <= 0 ? 0.0L : (long double)items[i].v / wi);
    }
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        if (dens[a] != dens[b]) return dens[a] > dens[b];
        return items[a].v > items[b].v;
    });

    auto eval = [&](const array<int,12>& x, long long& usedM, long long& usedL, long long& val) {
        __int128 um = 0, ul = 0, vv = 0;
        for (int i = 0; i < 12; i++) {
            um += (__int128)x[i] * items[i].m;
            ul += (__int128)x[i] * items[i].l;
            vv += (__int128)x[i] * items[i].v;
        }
        usedM = (long long)um;
        usedL = (long long)ul;
        val = (long long)vv;
    };

    auto refill_greedy = [&](array<int,12>& x) {
        long long usedM, usedL, val;
        eval(x, usedM, usedL, val);
        long long remM = M - usedM;
        long long remL = L - usedL;
        if (remM < 0 || remL < 0) return;
        for (int id : order) {
            int have = x[id];
            int canMore = items[id].q - have;
            if (canMore <= 0) continue;
            if (items[id].m > remM || items[id].l > remL) continue;
            long long add = min<long long>(canMore, min(remM / items[id].m, remL / items[id].l));
            if (add <= 0) continue;
            x[id] += (int)add;
            remM -= add * items[id].m;
            remL -= add * items[id].l;
        }
    };

    mt19937_64 rng(seed);

    Solution best = sol;
    if (best.usedM > M || best.usedL > L) {
        // repair (shouldn't happen)
        best.x.fill(0);
        best = greedy(items, M, L, 1.0L/(long double)M, 1.0L/(long double)L);
    }

    vector<int> nonzero;
    nonzero.reserve(12);

    for (int it = 0; it < ITER; it++) {
        array<int,12> x = best.x;

        nonzero.clear();
        for (int i = 0; i < 12; i++) if (x[i] > 0) nonzero.push_back(i);
        if (nonzero.empty()) break;

        int i = nonzero[(size_t)(rng() % nonzero.size())];

        int maxRemove = min(x[i], 30);
        if (maxRemove <= 0) continue;
        int r = 1 + (int)(rng() % maxRemove);

        x[i] -= r;

        // occasional second removal to escape local maxima
        if ((rng() % 5) == 0) {
            nonzero.clear();
            for (int j = 0; j < 12; j++) if (x[j] > 0) nonzero.push_back(j);
            if (!nonzero.empty()) {
                int j = nonzero[(size_t)(rng() % nonzero.size())];
                int maxRemove2 = min(x[j], 20);
                if (maxRemove2 > 0) {
                    int r2 = 1 + (int)(rng() % maxRemove2);
                    x[j] -= r2;
                }
            }
        }

        refill_greedy(x);

        long long usedM, usedL, val;
        eval(x, usedM, usedL, val);
        if (usedM <= M && usedL <= L && val > best.value) {
            best.x = x;
            best.value = val;
            best.usedM = usedM;
            best.usedL = usedL;
        }
    }

    return best;
}

static uint64_t hash_input(const string& s) {
    // FNV-1a 64-bit
    uint64_t h = 1469598103934665603ULL;
    for (unsigned char c : s) {
        h ^= (uint64_t)c;
        h *= 1099511628211ULL;
    }
    return h;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    size_t i = 0;
    skip_ws(input, i);
    if (i >= input.size() || input[i] != '{') return 0;
    i++;

    vector<Item> items;
    items.reserve(12);
    vector<string> keyOrder;

    while (true) {
        skip_ws(input, i);
        if (i >= input.size()) break;
        if (input[i] == '}') { i++; break; }

        string key = parse_string(input, i);
        skip_ws(input, i);
        if (i < input.size() && input[i] == ':') i++;
        skip_ws(input, i);
        if (i < input.size() && input[i] == '[') i++;
        long long q = parse_int(input, i);
        skip_ws(input, i); if (i < input.size() && input[i] == ',') i++;
        long long v = parse_int(input, i);
        skip_ws(input, i); if (i < input.size() && input[i] == ',') i++;
        long long m = parse_int(input, i);
        skip_ws(input, i); if (i < input.size() && input[i] == ',') i++;
        long long l = parse_int(input, i);
        skip_ws(input, i);
        if (i < input.size() && input[i] == ']') i++;

        Item it;
        it.name = key;
        it.q = (int)q;
        it.v = v;
        it.m = m;
        it.l = l;

        items.push_back(it);
        keyOrder.push_back(key);

        skip_ws(input, i);
        if (i < input.size() && input[i] == ',') { i++; continue; }
        if (i < input.size() && input[i] == '}') { i++; break; }
    }

    // Ensure exactly 12; if not, still proceed with min size but output what's given.
    int n = (int)items.size();
    if (n == 0) {
        cout << "{}\n";
        return 0;
    }
    if (n < 12) {
        // pad to 12 with dummies to keep code simple
        while ((int)items.size() < 12) {
            Item dummy;
            dummy.name = "__dummy" + to_string(items.size());
            dummy.q = 0;
            dummy.v = dummy.m = dummy.l = 0;
            items.push_back(dummy);
            keyOrder.push_back(dummy.name);
        }
    }
    if (n > 12) {
        items.resize(12);
        keyOrder.resize(12);
        n = 12;
    }

    const long long M = 20LL * 1000000LL;
    const long long L = 25LL * 1000000LL;

    vector<Solution> candidates;

    // Greedy candidates
    {
        long double invM = 1.0L / (long double)M;
        long double invL = 1.0L / (long double)L;
        vector<pair<long double,long double>> wts = {
            {1.0L, 0.0L},
            {0.0L, 1.0L},
            {invM, invL},
            {invM, 0.5L*invL},
            {invM, 2.0L*invL},
            {2.0L*invM, invL},
            {0.5L*invM, invL}
        };
        uint64_t h = hash_input(input);
        mt19937_64 rng(h ^ 0xA5A5A5A5A5A5A5A5ULL);
        for (int t = 0; t < 6; t++) {
            long double a = (long double)(rng() % 5000) / 1000.0L; // [0,5)
            long double b = (long double)(rng() % 5000) / 1000.0L; // [0,5)
            if (a < 0.05L && b < 0.05L) { a = invM; b = invL; }
            wts.push_back({a*invM, b*invL});
        }
        for (auto [a,b] : wts) candidates.push_back(greedy(items, M, L, a, b));
    }

    // Beam search candidates
    vector<WeightRun> runs;
    runs.push_back({1,1,true});
    runs.push_back({0,1,true});
    runs.push_back({1,4,true});
    runs.push_back({1,2,true});
    runs.push_back({2,1,true});
    runs.push_back({4,1,true});
    runs.push_back({8,1,true});
    runs.push_back({1,4,false});
    runs.push_back({1,2,false});
    runs.push_back({2,1,false});
    {
        uint64_t h = hash_input(input);
        mt19937_64 rng(h ^ 0x1234567890ABCDEFULL);
        for (int t = 0; t < 4; t++) {
            long long p = 1 + (long long)(rng() % 6);
            long long q = 1 + (long long)(rng() % 6);
            bool vol = (rng() & 1);
            runs.push_back({p,q,vol});
        }
    }

    int BEAM_W = 2500;
    for (auto &wr : runs) {
        candidates.push_back(beam_search(items, M, L, wr, BEAM_W));
    }

    // Choose best candidate
    Solution best;
    best.value = -1;
    for (auto &s : candidates) {
        auto used = compute_used(items, s.x);
        s.usedM = used.first;
        s.usedL = used.second;
        if (s.usedM <= M && s.usedL <= L && s.value > best.value) best = s;
    }

    // Local improvement on best
    {
        uint64_t seed = hash_input(input) ^ 0x9E3779B97F4A7C15ULL;
        best = local_improve(items, M, L, best, seed, 6000);
    }

    // Output JSON in original key order (first n keys)
    cout << "{\n";
    for (int k = 0; k < n; k++) {
        cout << " \"" << items[k].name << "\": " << best.x[k];
        if (k + 1 < n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";
    return 0;
}