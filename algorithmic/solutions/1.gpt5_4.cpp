#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
    int idx;
};

struct Parser {
    string s;
    size_t i = 0;
    Parser(const string& str): s(str), i(0) {}

    void skip_ws() {
        while (i < s.size() && isspace((unsigned char)s[i])) i++;
    }

    bool match(char c) {
        skip_ws();
        if (i < s.size() && s[i] == c) { i++; return true; }
        return false;
    }

    void expect(char c) {
        skip_ws();
        if (i >= s.size() || s[i] != c) {
            // Simple fail-safe: attempt to continue to avoid crash
            // in contest environment inputs are well-formed
            // but ensure we don't crash
            // Move on
            // For safety, move index to end
            i = s.size();
            return;
        }
        i++;
    }

    string parse_string() {
        skip_ws();
        expect('"');
        string res;
        while (i < s.size()) {
            char c = s[i++];
            if (c == '"') break;
            // No escaping assumed in problem statement
            res.push_back(c);
        }
        return res;
    }

    long long parse_int() {
        skip_ws();
        bool neg = false;
        if (i < s.size() && (s[i] == '-' || s[i] == '+')) {
            neg = (s[i] == '-');
            i++;
        }
        long long val = 0;
        while (i < s.size() && isdigit((unsigned char)s[i])) {
            val = val * 10 + (s[i++] - '0');
        }
        return neg ? -val : val;
    }

    vector<long long> parse_array_of_ints() {
        vector<long long> arr;
        skip_ws();
        expect('[');
        while (true) {
            skip_ws();
            if (i < s.size() && s[i] == ']') { i++; break; }
            long long num = parse_int();
            arr.push_back(num);
            skip_ws();
            if (i < s.size() && s[i] == ',') { i++; continue; }
            skip_ws();
            if (i < s.size() && s[i] == ']') { i++; break; }
        }
        return arr;
    }

    vector<Item> parse_items() {
        vector<Item> items;
        skip_ws();
        expect('{');
        int idx = 0;
        while (true) {
            skip_ws();
            if (i < s.size() && s[i] == '}') { i++; break; }
            string key = parse_string();
            skip_ws();
            expect(':');
            vector<long long> arr = parse_array_of_ints();
            Item it;
            it.name = key;
            if (arr.size() >= 4) {
                it.q = arr[0];
                it.v = arr[1];
                it.m = arr[2];
                it.l = arr[3];
            } else {
                it.q = it.v = it.m = it.l = 0;
            }
            it.idx = idx++;
            items.push_back(it);
            skip_ws();
            if (i < s.size() && s[i] == ',') { i++; continue; }
            skip_ws();
            if (i < s.size() && s[i] == '}') { i++; break; }
        }
        return items;
    }
};

struct Solution {
    vector<long long> x;
    long long value = 0;
    long long mass = 0;
    long long vol = 0;
};

struct Param {
    double am, al;
    int mode; // 0: linear combo; 2: max
    bool useRem;
};

static const long long MASS_CAP = 20000000LL;  // mg
static const long long VOL_CAP = 25000000LL;   // µl

inline long long clamp_ll(long long x, long long lo, long long hi) {
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

Solution greedyDynamic(const vector<Item>& items, const Param& p) {
    int n = (int)items.size();
    vector<long long> x(n, 0);
    long long remM = MASS_CAP, remL = VOL_CAP;
    long long val = 0;
    int safe_guard = 0;
    while (true) {
        int best = -1;
        long double bestScore = -1.0L;
        long double Mnorm = max(1LL, remM);
        long double Lnorm = max(1LL, remL);
        for (int i = 0; i < n; i++) {
            if (x[i] >= items[i].q) continue;
            if (items[i].m > remM || items[i].l > remL) continue;
            long double denom = 0.0;
            if (p.mode == 0) {
                long double mpart = (long double)items[i].m / (p.useRem ? Mnorm : (long double)MASS_CAP);
                long double lpart = (long double)items[i].l / (p.useRem ? Lnorm : (long double)VOL_CAP);
                denom = p.am * mpart + p.al * lpart;
            } else if (p.mode == 2) {
                long double mpart = (long double)items[i].m / (p.useRem ? Mnorm : (long double)MASS_CAP);
                long double lpart = (long double)items[i].l / (p.useRem ? Lnorm : (long double)VOL_CAP);
                denom = max(p.am * mpart, p.al * lpart);
            } else {
                // default linear
                long double mpart = (long double)items[i].m / (p.useRem ? Mnorm : (long double)MASS_CAP);
                long double lpart = (long double)items[i].l / (p.useRem ? Lnorm : (long double)VOL_CAP);
                denom = p.am * mpart + p.al * lpart;
            }
            if (denom <= 0) denom = 1e-18L; // safety
            long double score = (long double)items[i].v / denom;
            if (score > bestScore) {
                bestScore = score;
                best = i;
            }
        }
        if (best == -1) break;
        // add one
        x[best]++;
        remM -= items[best].m;
        remL -= items[best].l;
        val += items[best].v;
        if (++safe_guard > 1000000) break; // very safety guard
    }
    Solution s;
    s.x = move(x);
    s.value = val;
    s.mass = MASS_CAP - remM;
    s.vol = VOL_CAP - remL;
    return s;
}

bool try_add_with_removals(int j, vector<long long>& x, long long& totM, long long& totL, long long& totV, const vector<Item>& items) {
    if (x[j] >= items[j].q) return false;
    if (items[j].m > MASS_CAP || items[j].l > VOL_CAP) return false;
    long long remM = MASS_CAP - totM;
    long long remL = VOL_CAP - totL;

    if (items[j].m <= remM && items[j].l <= remL) {
        x[j] += 1;
        totM += items[j].m;
        totL += items[j].l;
        totV += items[j].v;
        return true;
    }

    long long needM = max(0LL, items[j].m - remM);
    long long needL = max(0LL, items[j].l - remL);

    // If impossible anyway due to individual constraints, return false
    if (items[j].m > MASS_CAP || items[j].l > VOL_CAP) return false;

    int n = (int)items.size();
    vector<long long> removed(n, 0);
    long long removedVal = 0;
    int steps = 0;
    while ((needM > 0 || needL > 0) && steps < 100000) {
        int best = -1;
        long double bestScore = LDBL_MAX;
        for (int i = 0; i < n; i++) {
            if (x[i] - removed[i] <= 0) continue;
            long double w = 0.0L;
            if (needM > 0) w += (long double)items[i].m / (long double)max(1LL, needM);
            if (needL > 0) w += (long double)items[i].l / (long double)max(1LL, needL);
            if (w <= 0.0L) continue;
            long double score = (long double)items[i].v / w; // minimize
            if (score < bestScore) {
                bestScore = score;
                best = i;
            }
        }
        if (best == -1) break;
        removed[best] += 1;
        removedVal += items[best].v;
        needM -= items[best].m;
        needL -= items[best].l;
        if (removedVal >= items[j].v) {
            // No longer beneficial
            break;
        }
        steps++;
    }

    if (needM <= 0 && needL <= 0 && removedVal < items[j].v) {
        // Accept
        x[j] += 1;
        totM += items[j].m;
        totL += items[j].l;
        totV += items[j].v;
        for (int i = 0; i < n; i++) {
            if (removed[i] > 0) {
                x[i] -= removed[i];
                totM -= items[i].m * removed[i];
                totL -= items[i].l * removed[i];
                totV -= items[i].v * removed[i];
            }
        }
        return true;
    }
    return false;
}

void improve_solution(vector<long long>& x, long long& totM, long long& totL, long long& totV, const vector<Item>& items) {
    int n = (int)items.size();
    // Simple iterative improvement: try to add higher value items by removing lower value ones if beneficial.
    int iter = 0;
    while (iter < 50) {
        bool any = false;
        // Try to greedily add items in order of descending value density relative to current remaining capacity
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        long double remM = max(1LL, MASS_CAP - totM);
        long double remL = max(1LL, VOL_CAP - totL);
        sort(order.begin(), order.end(), [&](int a, int b) {
            // density w.r.t. current rem normalized (balanced)
            long double wa = (long double)items[a].m / remM + (long double)items[a].l / remL;
            long double wb = (long double)items[b].m / remM + (long double)items[b].l / remL;
            long double da = (wa > 0 ? (long double)items[a].v / wa : (long double)items[a].v * 1e18L);
            long double db = (wb > 0 ? (long double)items[b].v / wb : (long double)items[b].v * 1e18L);
            if (da != db) return da > db;
            return items[a].v > items[b].v;
        });

        for (int idx = 0; idx < n; idx++) {
            int j = order[idx];
            // attempt multiple times if possible
            int tries = 0;
            while (tries < 1000) {
                long long beforeV = totV;
                if (!try_add_with_removals(j, x, totM, totL, totV, items)) break;
                if (totV <= beforeV) break; // safety
                any = true;
                tries++;
            }
        }
        // Try simple pairwise swaps that are beneficial
        for (int j = 0; j < n; j++) {
            if (items[j].m > MASS_CAP || items[j].l > VOL_CAP) continue;
            // Try swapping with each i
            for (int i = 0; i < n; i++) {
                if (x[i] <= 0) continue;
                if (x[j] >= items[j].q) continue;
                long long newM = totM + items[j].m - items[i].m;
                long long newL = totL + items[j].l - items[i].l;
                if (newM <= MASS_CAP && newL <= VOL_CAP && items[j].v > items[i].v) {
                    // perform swap
                    x[i]--; x[j]++;
                    totM = newM;
                    totL = newL;
                    totV += items[j].v - items[i].v;
                    any = true;
                }
            }
        }

        if (!any) break;
        iter++;
    }
}

Solution one_type_only(const vector<Item>& items) {
    int n = (int)items.size();
    Solution best;
    best.x.assign(n, 0);
    best.value = 0; best.mass = 0; best.vol = 0;
    for (int i = 0; i < n; i++) {
        long long k1 = items[i].m ? (MASS_CAP / items[i].m) : (long long)4e18;
        long long k2 = items[i].l ? (VOL_CAP / items[i].l) : (long long)4e18;
        long long k = min({items[i].q, k1, k2});
        if (k < 0) k = 0;
        long long v = k * items[i].v;
        if (v > best.value) {
            best.value = v;
            best.mass = k * items[i].m;
            best.vol = k * items[i].l;
            best.x.assign(n, 0);
            best.x[i] = k;
        }
    }
    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire stdin into string
    string input, line;
    {
        ostringstream oss;
        oss << cin.rdbuf();
        input = oss.str();
    }

    Parser parser(input);
    vector<Item> items = parser.parse_items();
    int n = (int)items.size();

    // Parameters for greedy strategies
    vector<Param> params;
    vector<double> betas = {0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 4.0};
    for (double b : betas) {
        params.push_back({1.0, b, 0, true});
        params.push_back({b, 1.0, 0, true});
    }
    // mass-only and volume-only
    params.push_back({1.0, 0.0, 0, true});
    params.push_back({0.0, 1.0, 0, true});
    // max-mode
    params.push_back({1.0, 1.0, 2, true});

    // Evaluate all strategies and keep the best
    Solution best;
    best.x.assign(n, 0);
    best.value = 0;
    best.mass = 0;
    best.vol = 0;

    // Include one-type-only baseline
    {
        Solution s = one_type_only(items);
        if (s.value > best.value) best = s;
    }

    for (const auto& p : params) {
        Solution s = greedyDynamic(items, p);
        // improve
        vector<long long> x = s.x;
        long long totM = s.mass, totL = s.vol, totV = s.value;
        improve_solution(x, totM, totL, totV, items);
        s.x = x; s.mass = totM; s.vol = totL; s.value = totV;
        if (s.value > best.value) best = s;
    }

    // Ensure feasibility (should be)
    long long chkM = 0, chkL = 0;
    for (int i = 0; i < n; i++) {
        if (best.x[i] < 0) best.x[i] = 0;
        if (best.x[i] > items[i].q) best.x[i] = items[i].q;
        chkM += best.x[i] * items[i].m;
        chkL += best.x[i] * items[i].l;
    }
    if (chkM > MASS_CAP || chkL > VOL_CAP) {
        // Fallback to empty if somehow infeasible (very unlikely)
        best.x.assign(n, 0);
    }

    // Output JSON with same keys
    cout << "{\n";
    for (int i = 0; i < n; i++) {
        cout << " \"" << items[i].name << "\": " << best.x[i];
        if (i + 1 < n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";

    return 0;
}