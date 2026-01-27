#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
    double nm, nl;
};

struct Parser {
    string s;
    size_t i = 0;

    Parser(const string& str): s(str), i(0) {}

    void skipWS() {
        while (i < s.size() && isspace((unsigned char)s[i])) i++;
    }

    bool consume(char c) {
        skipWS();
        if (i < s.size() && s[i] == c) { i++; return true; }
        return false;
    }

    void expect(char c) {
        skipWS();
        if (i >= s.size() || s[i] != c) {
            // Fail gracefully by advancing to end
            throw runtime_error("JSON parse error: expected char");
        }
        i++;
    }

    string parseString() {
        skipWS();
        if (i >= s.size() || s[i] != '"') throw runtime_error("JSON parse error: expected string");
        i++;
        string res;
        while (i < s.size()) {
            char c = s[i++];
            if (c == '"') break;
            // No escapes expected per problem statement (lowercase ascii)
            res.push_back(c);
        }
        return res;
    }

    long long parseNumber() {
        skipWS();
        bool neg = false;
        if (i < s.size() && s[i] == '-') { neg = true; i++; }
        long long val = 0;
        bool any = false;
        while (i < s.size() && isdigit((unsigned char)s[i])) {
            any = true;
            val = val * 10 + (s[i] - '0');
            i++;
        }
        if (!any) throw runtime_error("JSON parse error: expected number");
        return neg ? -val : val;
    }

    vector<long long> parseArrayOfNumbers() {
        skipWS();
        expect('[');
        vector<long long> nums;
        while (true) {
            skipWS();
            if (consume(']')) break;
            long long num = parseNumber();
            nums.push_back(num);
            skipWS();
            if (consume(']')) break;
            consume(',');
        }
        return nums;
    }

    vector<Item> parseItems() {
        skipWS();
        expect('{');
        vector<Item> items;
        while (true) {
            skipWS();
            if (consume('}')) break;
            string key = parseString();
            skipWS();
            expect(':');
            vector<long long> arr = parseArrayOfNumbers();
            // Expect at least 4 numbers: q, v, m, l
            long long q = 0, v = 0, m = 0, l = 0;
            if (arr.size() >= 4) {
                q = arr[0]; v = arr[1]; m = arr[2]; l = arr[3];
            } else {
                throw runtime_error("JSON parse error: array size < 4");
            }
            Item it; it.name = key; it.q = q; it.v = v; it.m = m; it.l = l;
            items.push_back(it);
            skipWS();
            if (consume('}')) break;
            consume(',');
        }
        return items;
    }
};

static const long long M_CAP = 20000000LL; // 20 kg in mg
static const long long L_CAP = 25000000LL; // 25 L in uL

struct Solution {
    vector<long long> x;
    long long val = 0;
    long long remM = M_CAP;
    long long remL = L_CAP;
};

long long computeValue(const vector<Item>& items, const vector<long long>& x) {
    long long val = 0;
    for (size_t i = 0; i < items.size(); ++i) {
        val += x[i] * items[i].v;
    }
    return val;
}

Solution greedy_with_order(const vector<Item>& items, const vector<int>& order) {
    Solution sol;
    int n = (int)items.size();
    sol.x.assign(n, 0);
    sol.remM = M_CAP;
    sol.remL = L_CAP;
    for (int idx : order) {
        const Item& it = items[idx];
        if (it.m > sol.remM || it.l > sol.remL) {
            long long canM = (it.m == 0) ? it.q : (sol.remM / it.m);
            long long canL = (it.l == 0) ? it.q : (sol.remL / it.l);
            long long can = min({it.q, canM, canL});
            // If can't place even one, continue
            if (can <= 0) continue;
            sol.x[idx] += can;
            sol.remM -= can * it.m;
            sol.remL -= can * it.l;
        } else {
            long long canM = (it.m == 0) ? it.q : (sol.remM / it.m);
            long long canL = (it.l == 0) ? it.q : (sol.remL / it.l);
            long long can = min({it.q, canM, canL});
            if (can <= 0) continue;
            sol.x[idx] += can;
            sol.remM -= can * it.m;
            sol.remL -= can * it.l;
        }
    }
    sol.val = computeValue(items, sol.x);
    return sol;
}

vector<int> order_by_metric(const vector<Item>& items, function<double(const Item&)> metric) {
    int n = (int)items.size();
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    vector<double> score(n);
    for (int i = 0; i < n; ++i) score[i] = metric(items[i]);
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        if (score[a] == score[b]) {
            // tie-breaker: higher value, then smaller combined size
            if (items[a].v != items[b].v) return items[a].v > items[b].v;
            long long sa = items[a].m + items[a].l;
            long long sb = items[b].m + items[b].l;
            if (sa != sb) return sa < sb;
            return a < b;
        }
        return score[a] > score[b];
    });
    return order;
}

void init_norms(vector<Item>& items) {
    for (auto &it : items) {
        it.nm = (double)it.m / (double)M_CAP;
        it.nl = (double)it.l / (double)L_CAP;
    }
}

bool try_add_with_removal(const vector<Item>& items, Solution& sol, int i) {
    const Item& it = items[i];
    if (sol.x[i] >= it.q) return false;

    // If item doesn't fit in bag at all, skip
    if (it.m > M_CAP || it.l > L_CAP) return false;

    // Try to add as many as profitable, at least one
    bool improved = false;
    // Limit number of attempts to avoid long loops when items are tiny
    int tryLimit = 100000; // effectively unlimited, but safe guard
    while (sol.x[i] < it.q && tryLimit-- > 0) {
        if (it.m <= sol.remM && it.l <= sol.remL) {
            sol.x[i] += 1;
            sol.remM -= it.m;
            sol.remL -= it.l;
            sol.val += it.v;
            improved = true;
            continue;
        }
        long long needM = max(0LL, it.m - sol.remM);
        long long needL = max(0LL, it.l - sol.remL);
        if (needM <= 0 && needL <= 0) {
            // Should not happen due to previous if, but guard
            sol.x[i] += 1;
            sol.remM -= it.m;
            sol.remL -= it.l;
            sol.val += it.v;
            improved = true;
            continue;
        }

        // Build list of removable types with x>0
        struct Cand { int idx; double ratio; };
        vector<Cand> cands;
        double alpha = (double)needM; // scaling factors (unscaled)
        double beta  = (double)needL;
        for (int j = 0; j < (int)items.size(); ++j) {
            if (sol.x[j] <= 0) continue;
            double denom = alpha * (double)items[j].m + beta * (double)items[j].l;
            if (denom <= 0) continue; // if denom 0, this item doesn't help free needed resource
            double r = (double)items[j].v / denom; // value per unit of needed freeing
            cands.push_back({j, r});
        }
        if (cands.empty()) {
            // Cannot free anything
            break;
        }
        sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b){
            if (a.ratio == b.ratio) return a.idx < b.idx;
            return a.ratio < b.ratio; // remove worst first
        });

        long long freedM = 0, freedL = 0;
        long long removedValue = 0;
        vector<pair<int,long long>> plan; // (j, cnt)
        long long needM_left = needM;
        long long needL_left = needL;

        for (auto &c : cands) {
            if (needM_left <= 0 && needL_left <= 0) break;
            int j = c.idx;
            long long have = sol.x[j];
            if (have <= 0) continue;
            long long mj = items[j].m;
            long long lj = items[j].l;

            // Count needed from this item to cover remaining deficits
            long long tM = (needM_left > 0 && mj > 0) ? ( (needM_left + mj - 1) / mj ) : 0;
            long long tL = (needL_left > 0 && lj > 0) ? ( (needL_left + lj - 1) / lj ) : 0;
            long long t = max(tM, tL);
            if (t <= 0) continue;
            if (t > have) t = have;

            freedM += t * mj;
            freedL += t * lj;
            removedValue += t * items[j].v;
            plan.push_back({j, t});

            // Update remaining need
            if (freedM >= needM) needM_left = 0;
            else needM_left = needM - freedM;
            if (freedL >= needL) needL_left = 0;
            else needL_left = needL - freedL;
        }

        if (needM_left > 0 || needL_left > 0) {
            // Even removing everything we picked we can't free enough - give up for this item
            break;
        }

        if (it.v > removedValue) {
            // Apply removal and add
            for (auto &pr : plan) {
                int j = pr.first;
                long long t = pr.second;
                sol.x[j] -= t;
                sol.remM += t * items[j].m;
                sol.remL += t * items[j].l;
                sol.val -= t * items[j].v;
            }
            // Now we have enough
            sol.x[i] += 1;
            sol.remM -= it.m;
            sol.remL -= it.l;
            sol.val += it.v;
            improved = true;
            continue;
        } else {
            // Not profitable to add this item by removing others
            break;
        }
    }
    return improved;
}

void improve_solution(const vector<Item>& items, Solution& sol, double time_limit_sec) {
    auto t0 = chrono::steady_clock::now();
    int n = (int)items.size();

    // Precompute a default ordering by value density over combined normalized usage
    auto norm_metric = [&](const Item& it)->double {
        double denom = it.nm + it.nl;
        if (denom <= 0) denom = 1e-12;
        return (double)it.v / denom;
    };
    vector<int> order = order_by_metric(items, norm_metric);

    while (true) {
        auto t1 = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(t1 - t0).count();
        if (elapsed > time_limit_sec) break;

        bool any = false;

        // Try to greedily add high-density items possibly removing worse ones
        for (int idx = 0; idx < n; ++idx) {
            int i = order[idx];
            bool changed = try_add_with_removal(items, sol, i);
            if (changed) any = true;

            auto t2 = chrono::steady_clock::now();
            double elapsed2 = chrono::duration<double>(t2 - t0).count();
            if (elapsed2 > time_limit_sec) break;
        }

        if (!any) break;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire input
    string input, line;
    {
        ostringstream oss;
        string tmp;
        while (getline(cin, tmp)) {
            oss << tmp << '\n';
        }
        input = oss.str();
    }

    vector<Item> items;
    try {
        Parser parser(input);
        items = parser.parseItems();
    } catch (...) {
        // If parsing fails, produce empty output in same structure (fallback)
        // But we'll just try to parse again or exit; for safety default.
        // As per problem constraints, input should be valid.
    }

    int n = (int)items.size();
    init_norms(items);

    // Generate multiple candidate orders based on different metrics
    vector<vector<int>> orders;

    // Combined weighted by lambda
    vector<double> lambdas = {0.0, 0.2, 0.5, 0.8, 1.0};
    for (double lam : lambdas) {
        auto metric = [lam](const Item& it)->double {
            double denom = lam * it.nm + (1.0 - lam) * it.nl;
            if (denom <= 0) denom = 1e-12;
            return (double)it.v / denom;
        };
        orders.push_back(order_by_metric(items, metric));
    }

    // v/m
    orders.push_back(order_by_metric(items, [](const Item& it)->double {
        double denom = (double)it.m;
        if (denom <= 0) denom = 1e-12;
        return (double)it.v / denom;
    }));
    // v/l
    orders.push_back(order_by_metric(items, [](const Item& it)->double {
        double denom = (double)it.l;
        if (denom <= 0) denom = 1e-12;
        return (double)it.v / denom;
    }));
    // v / (nm + nl)
    orders.push_back(order_by_metric(items, [](const Item& it)->double {
        double denom = it.nm + it.nl;
        if (denom <= 0) denom = 1e-12;
        return (double)it.v / denom;
    }));
    // v / max(nm, nl)
    orders.push_back(order_by_metric(items, [](const Item& it)->double {
        double denom = max(it.nm, it.nl);
        if (denom <= 0) denom = 1e-12;
        return (double)it.v / denom;
    }));
    // v / hypot(nm, nl)
    orders.push_back(order_by_metric(items, [](const Item& it)->double {
        double denom = hypot(it.nm, it.nl);
        if (denom <= 0) denom = 1e-12;
        return (double)it.v / denom;
    }));
    // pure value
    orders.push_back(order_by_metric(items, [](const Item& it)->double {
        return (double)it.v;
    }));

    // Generate candidate solutions
    Solution best;
    best.x.assign(n, 0);
    best.val = -1;
    best.remM = M_CAP;
    best.remL = L_CAP;

    for (auto &ord : orders) {
        Solution sol = greedy_with_order(items, ord);
        if (sol.val > best.val) best = sol;
    }

    // Improvement step with time budget
    improve_solution(items, best, 0.85);

    // Output JSON with same keys in input order
    cout << "{\n";
    for (int i = 0; i < n; ++i) {
        cout << " \"" << items[i].name << "\": " << (best.x[i] < 0 ? 0 : best.x[i]);
        if (i + 1 < n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";
    return 0;
}