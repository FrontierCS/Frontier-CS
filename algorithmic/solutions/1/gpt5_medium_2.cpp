#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
};

struct Parser {
    string s;
    size_t p = 0;

    Parser(const string& str): s(str), p(0) {}

    void skip_ws() {
        while (p < s.size() && (s[p] == ' ' || s[p] == '\n' || s[p] == '\r' || s[p] == '\t')) p++;
    }

    bool match(char c) {
        skip_ws();
        if (p < s.size() && s[p] == c) { p++; return true; }
        return false;
    }

    void expect(char c) {
        skip_ws();
        if (p >= s.size() || s[p] != c) {
            // Simple fallback in case of malformed input
            throw runtime_error("JSON parse error: expected char not found");
        }
        p++;
    }

    string parse_string() {
        skip_ws();
        expect('"');
        string res;
        while (p < s.size()) {
            char c = s[p++];
            if (c == '"') break;
            if (c == '\\') {
                if (p >= s.size()) break;
                char esc = s[p++];
                // Only handle simple escapes; per problem, shouldn't appear.
                if (esc == '"' || esc == '\\' || esc == '/') res.push_back(esc);
                else if (esc == 'b') res.push_back('\b');
                else if (esc == 'f') res.push_back('\f');
                else if (esc == 'n') res.push_back('\n');
                else if (esc == 'r') res.push_back('\r');
                else if (esc == 't') res.push_back('\t');
                else res.push_back(esc);
            } else {
                res.push_back(c);
            }
        }
        return res;
    }

    long long parse_int() {
        skip_ws();
        bool neg = false;
        if (p < s.size() && (s[p] == '-' || s[p] == '+')) {
            neg = (s[p] == '-');
            p++;
        }
        long long val = 0;
        bool hasDigits = false;
        while (p < s.size() && isdigit((unsigned char)s[p])) {
            hasDigits = true;
            val = val * 10 + (s[p]-'0');
            p++;
        }
        if (!hasDigits) throw runtime_error("JSON parse error: expected integer");
        return neg ? -val : val;
    }

    vector<long long> parse_array() {
        vector<long long> arr;
        expect('[');
        skip_ws();
        bool first = true;
        while (true) {
            skip_ws();
            if (match(']')) break;
            if (!first) expect(',');
            first = false;
            long long x = parse_int();
            arr.push_back(x);
            skip_ws();
        }
        return arr;
    }

    vector<Item> parse_object() {
        vector<Item> items;
        expect('{');
        bool first = true;
        while (true) {
            skip_ws();
            if (match('}')) break;
            if (!first) expect(',');
            first = false;
            string key = parse_string();
            skip_ws();
            expect(':');
            vector<long long> arr = parse_array();
            if (arr.size() != 4) throw runtime_error("JSON parse error: array length != 4");
            Item it;
            it.name = key;
            it.q = arr[0];
            it.v = arr[1];
            it.m = arr[2];
            it.l = arr[3];
            items.push_back(it);
        }
        return items;
    }
};

struct Solution {
    vector<long long> x;
    long long mass = 0;
    long long vol = 0;
    long long val = 0;
};

const long long Mcap = 20000000LL;
const long long Lcap = 25000000LL;

void greedy_fill(Solution& sol, const vector<Item>& items, const vector<int>& order) {
    for (int idx : order) {
        const Item& it = items[idx];
        if (sol.mass >= Mcap || sol.vol >= Lcap) break;
        long long remM = Mcap - sol.mass;
        long long remL = Lcap - sol.vol;
        long long byM = (it.m > 0) ? (remM / it.m) : 0;
        long long byL = (it.l > 0) ? (remL / it.l) : 0;
        long long canAdd = min({ it.q - sol.x[idx], byM, byL });
        if (canAdd > 0) {
            sol.x[idx] += canAdd;
            sol.mass += canAdd * it.m;
            sol.vol  += canAdd * it.l;
            sol.val  += canAdd * it.v;
        }
    }
}

bool try_remove_and_fill(Solution& sol, const vector<Item>& items, const vector<int>& order, const vector<pair<int,int>>& removals) {
    Solution old = sol;
    // Apply removals
    for (auto [i, k] : removals) {
        if (k <= 0) continue;
        if (i < 0 || i >= (int)items.size()) { sol = old; return false; }
        if (sol.x[i] < k) { sol = old; return false; }
        sol.x[i] -= k;
        sol.mass -= 1LL * k * items[i].m;
        sol.vol  -= 1LL * k * items[i].l;
        sol.val  -= 1LL * k * items[i].v;
        if (sol.mass < 0 || sol.vol < 0) { sol = old; return false; }
    }
    greedy_fill(sol, items, order);
    if (sol.val > old.val) {
        return true;
    } else {
        sol = old;
        return false;
    }
}

Solution build_solution_alpha(const vector<Item>& items, double alpha) {
    int n = (int)items.size();
    vector<double> score(n);
    for (int i = 0; i < n; ++i) {
        double denom = alpha * (double)items[i].m / (double)Mcap + (1.0 - alpha) * (double)items[i].l / (double)Lcap;
        if (denom <= 0) denom = 1e-18;
        score[i] = (double)items[i].v / denom;
    }
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        if (score[a] != score[b]) return score[a] > score[b];
        // Tie-breakers
        double d1 = (double)items[a].v / ((double)items[a].m / (double)Mcap + (double)items[a].l / (double)Lcap);
        double d2 = (double)items[b].v / ((double)items[b].m / (double)Mcap + (double)items[b].l / (double)Lcap);
        if (d1 != d2) return d1 > d2;
        return items[a].v > items[b].v;
    });

    Solution sol;
    sol.x.assign(n, 0);
    greedy_fill(sol, items, order);

    // Improvement phase
    vector<int> orderAsc = order;
    reverse(orderAsc.begin(), orderAsc.end()); // worst to best by score
    const int maxSingleRemove = 5;
    const int maxPairRemove = 3;

    bool improved = true;
    int outerIters = 0;
    while (improved && outerIters < 200) {
        improved = false;
        outerIters++;

        // Try single-type removals (remove up to k items from a low-scoring type)
        for (int idx : orderAsc) {
            if (sol.x[idx] <= 0) continue;
            int lim = (int)min<long long>(maxSingleRemove, sol.x[idx]);
            for (int k = 1; k <= lim; ++k) {
                if (try_remove_and_fill(sol, items, order, { {idx, k} })) {
                    improved = true;
                    break;
                }
            }
            if (improved) break;
        }
        if (improved) continue;

        // Try pair removals
        for (int a = 0; a < (int)orderAsc.size() && !improved; ++a) {
            int i = orderAsc[a];
            if (sol.x[i] <= 0) continue;
            int limi = (int)min<long long>(maxPairRemove, sol.x[i]);
            for (int b = a; b < (int)orderAsc.size() && !improved; ++b) {
                int j = orderAsc[b];
                if (sol.x[j] <= 0) continue;
                int limj = (int)min<long long>(maxPairRemove, sol.x[j]);
                for (int ki = 1; ki <= limi && !improved; ++ki) {
                    for (int kj = 1; kj <= limj && !improved; ++kj) {
                        if (i == j && ki + kj > sol.x[i]) break;
                        vector<pair<int,int>> rems;
                        if (i == j) rems.push_back({i, ki + kj});
                        else { rems.push_back({i, ki}); rems.push_back({j, kj}); }
                        if (try_remove_and_fill(sol, items, order, rems)) {
                            improved = true;
                            break;
                        }
                    }
                }
            }
        }
    }

    return sol;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    Parser parser(input);
    vector<Item> items;
    try {
        items = parser.parse_object();
    } catch (...) {
        // If parsing fails, output zeros for robustness
        cout << "{\n";
        for (size_t i = 0; i < items.size(); ++i) {
            cout << " \"" << items[i].name << "\": 0";
            if (i + 1 != items.size()) cout << ",\n"; else cout << "\n";
        }
        cout << "}\n";
        return 0;
    }

    int n = (int)items.size();
    // Prepare alphas to try
    vector<double> alphas;
    for (int i = 0; i <= 10; ++i) alphas.push_back(i / 10.0);
    alphas.push_back(0.33);
    alphas.push_back(0.67);

    Solution best;
    best.x.assign(n, 0);
    best.val = -1;

    for (double a : alphas) {
        Solution sol = build_solution_alpha(items, a);
        if (sol.val > best.val) best = sol;
    }

    // Final pass: try improving the best solution using a different ordering set
    // Re-run improvement with all alpha orderings to squeeze more value
    for (double a : alphas) {
        // Build order for this alpha
        vector<double> score(n);
        for (int i = 0; i < n; ++i) {
            double denom = a * (double)items[i].m / (double)Mcap + (1.0 - a) * (double)items[i].l / (double)Lcap;
            if (denom <= 0) denom = 1e-18;
            score[i] = (double)items[i].v / denom;
        }
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        stable_sort(order.begin(), order.end(), [&](int u, int v){
            if (score[u] != score[v]) return score[u] > score[v];
            return items[u].v > items[v].v;
        });
        // Try local improvements on a copy of best
        Solution sol = best;
        greedy_fill(sol, items, order);
        // Local improve small
        vector<int> orderAsc = order;
        reverse(orderAsc.begin(), orderAsc.end());
        bool improved = true;
        int iter = 0;
        while (improved && iter < 100) {
            improved = false;
            iter++;
            for (int idx : orderAsc) {
                if (sol.x[idx] <= 0) continue;
                int lim = (int)min<long long>(5, sol.x[idx]);
                for (int k = 1; k <= lim; ++k) {
                    if (try_remove_and_fill(sol, items, order, { {idx, k} })) {
                        improved = true;
                        break;
                    }
                }
                if (improved) break;
            }
        }
        if (sol.val > best.val) best = sol;
    }

    // Ensure feasibility (should be)
    // Output JSON
    cout << "{\n";
    for (int i = 0; i < n; ++i) {
        cout << " \"" << items[i].name << "\": " << best.x[i];
        if (i + 1 != n) cout << ",\n"; else cout << "\n";
    }
    cout << "}\n";
    return 0;
}