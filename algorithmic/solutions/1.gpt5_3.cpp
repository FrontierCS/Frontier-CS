#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
};

struct Solution {
    vector<long long> x;
    long long value = 0;
    long long mass = 0;
    long long vol = 0;
};

static const long long M_CAP = 20LL * 1000000LL; // 20 kg in mg
static const long long L_CAP = 25LL * 1000000LL; // 25 L in µL

struct Parser {
    string s;
    size_t i = 0;

    Parser(const string& str): s(str), i(0) {}

    void skipWS() {
        while (i < s.size() && isspace((unsigned char)s[i])) i++;
    }

    bool match(char c) {
        skipWS();
        if (i < s.size() && s[i] == c) {
            i++;
            return true;
        }
        return false;
    }

    void expect(char c) {
        skipWS();
        if (i >= s.size() || s[i] != c) {
            // invalid JSON for our purposes; just proceed
        } else {
            i++;
        }
    }

    string parseString() {
        skipWS();
        string res;
        if (i < s.size() && s[i] == '"') {
            i++;
            while (i < s.size()) {
                char c = s[i++];
                if (c == '"') break;
                if (c == '\\') {
                    if (i < s.size()) {
                        char esc = s[i++];
                        // For simplicity, handle only common escapes
                        if (esc == '"' || esc == '\\' || esc == '/')
                            res.push_back(esc);
                        else if (esc == 'b') res.push_back('\b');
                        else if (esc == 'f') res.push_back('\f');
                        else if (esc == 'n') res.push_back('\n');
                        else if (esc == 'r') res.push_back('\r');
                        else if (esc == 't') res.push_back('\t');
                        else res.push_back(esc);
                    }
                } else {
                    res.push_back(c);
                }
            }
        }
        return res;
    }

    long long parseNumber() {
        skipWS();
        long long sign = 1;
        if (i < s.size() && (s[i] == '+' || s[i] == '-')) {
            if (s[i] == '-') sign = -1;
            i++;
        }
        long long num = 0;
        while (i < s.size() && isdigit((unsigned char)s[i])) {
            num = num * 10 + (s[i] - '0');
            i++;
        }
        return sign * num;
    }

    vector<long long> parseArrayNumbers() {
        vector<long long> arr;
        expect('[');
        while (true) {
            skipWS();
            if (i < s.size() && s[i] == ']') { i++; break; }
            long long num = parseNumber();
            arr.push_back(num);
            skipWS();
            if (i < s.size() && s[i] == ',') {
                i++;
                continue;
            } else if (i < s.size() && s[i] == ']') {
                i++;
                break;
            } else {
                // malformed, break
                break;
            }
        }
        return arr;
    }

    vector<Item> parseObject() {
        vector<Item> items;
        expect('{');
        while (true) {
            skipWS();
            if (i < s.size() && s[i] == '}') { i++; break; }
            string key = parseString();
            skipWS();
            expect(':');
            vector<long long> arr = parseArrayNumbers();
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
            items.push_back(it);
            skipWS();
            if (i < s.size() && s[i] == ',') {
                i++;
                continue;
            } else if (i < s.size() && s[i] == '}') {
                i++;
                break;
            } else {
                // End or malformed; break
                break;
            }
        }
        return items;
    }
};

struct OrderDesc {
    int kind; // 0 = weighted sum, 1 = max norm, 2 = euclidean
    double alpha; // for kind 0
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire stdin
    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    Parser parser(input);
    vector<Item> items = parser.parseObject();
    int n = (int)items.size();
    if (n == 0) {
        cout << "{\n}\n";
        return 0;
    }

    // Limits
    const long long M = M_CAP;
    const long long L = L_CAP;

    vector<long long> q(n), v(n), m(n), l(n);
    vector<string> names(n);
    for (int i = 0; i < n; ++i) {
        names[i] = items[i].name;
        q[i] = items[i].q;
        v[i] = items[i].v;
        m[i] = items[i].m;
        l[i] = items[i].l;
    }

    // Cap q by capacity constraints
    vector<long long> qCap(n);
    for (int i = 0; i < n; ++i) {
        long long byM = (m[i] > 0 ? M / m[i] : 0);
        long long byL = (l[i] > 0 ? L / l[i] : 0);
        long long cap = min(byM, byL);
        if (cap < 0) cap = 0;
        if (cap > q[i]) cap = q[i];
        qCap[i] = cap;
    }

    // Precompute normalized weights
    vector<double> mN(n), lN(n);
    for (int i = 0; i < n; ++i) {
        mN[i] = (double)m[i] / (double)M;
        lN[i] = (double)l[i] / (double)L;
    }

    auto build_order = [&](const OrderDesc& od)->vector<int> {
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);
        vector<double> ratio(n, 0.0);
        for (int i = 0; i < n; ++i) {
            double cw = 0.0;
            if (od.kind == 0) {
                cw = od.alpha * mN[i] + (1.0 - od.alpha) * lN[i];
            } else if (od.kind == 1) {
                cw = max(mN[i], lN[i]);
            } else {
                double a = mN[i], b = lN[i];
                cw = sqrt(a*a + b*b);
            }
            if (cw <= 0.0) cw = 1e-18;
            ratio[i] = (double)v[i] / cw;
        }
        stable_sort(idx.begin(), idx.end(), [&](int a, int b) {
            if (ratio[a] != ratio[b]) return ratio[a] > ratio[b];
            if (v[a] != v[b]) return v[a] > v[b];
            // Tie-break by smaller combined weight utilization
            double wa = mN[a] + lN[a];
            double wb = mN[b] + lN[b];
            if (wa != wb) return wa < wb;
            return a < b;
        });
        return idx;
    };

    auto compute_value = [&](const vector<long long>& x)->long long {
        long long res = 0;
        for (int i = 0; i < n; ++i) res += x[i] * v[i];
        return res;
    };
    auto compute_mass = [&](const vector<long long>& x)->long long {
        long long res = 0;
        for (int i = 0; i < n; ++i) res += x[i] * m[i];
        return res;
    };
    auto compute_vol = [&](const vector<long long>& x)->long long {
        long long res = 0;
        for (int i = 0; i < n; ++i) res += x[i] * l[i];
        return res;
    };

    auto greedy_fill_order = [&](const vector<int>& order, const vector<long long>& xStart)->Solution {
        Solution sol;
        sol.x = xStart;
        long long massUsed = 0, volUsed = 0;
        for (int i = 0; i < n; ++i) {
            if (sol.x[i] < 0) sol.x[i] = 0;
            if (sol.x[i] > qCap[i]) sol.x[i] = qCap[i];
            massUsed += sol.x[i] * m[i];
            volUsed += sol.x[i] * l[i];
        }
        if (massUsed > M || volUsed > L) {
            // If invalid, clamp down everything (should not happen)
            sol.x.assign(n, 0);
            massUsed = volUsed = 0;
        }

        for (int idx : order) {
            if (qCap[idx] <= sol.x[idx]) continue;
            if (m[idx] == 0 || l[idx] == 0) continue; // should not happen
            if (massUsed >= M || volUsed >= L) break;
            long long mm = M - massUsed;
            long long vv = L - volUsed;
            long long t1 = mm / m[idx];
            long long t2 = vv / l[idx];
            long long t = min({t1, t2, qCap[idx] - sol.x[idx]});
            if (t > 0) {
                sol.x[idx] += t;
                massUsed += t * m[idx];
                volUsed += t * l[idx];
            }
        }
        sol.mass = massUsed;
        sol.vol = volUsed;
        sol.value = compute_value(sol.x);
        return sol;
    };

    // Build orders
    vector<OrderDesc> ordersDesc;
    // Weighted sums over a spread of alphas
    vector<double> alphas = {0.0, 0.15, 0.25, 0.35, 0.5, 0.65, 0.75, 0.85, 1.0};
    for (double a : alphas) ordersDesc.push_back({0, a});
    // Additional norms
    ordersDesc.push_back({1, 0.0}); // max norm
    ordersDesc.push_back({2, 0.0}); // euclidean

    vector<vector<int>> orders;
    for (auto& od : ordersDesc) orders.push_back(build_order(od));

    // Initial solutions
    vector<Solution> candidates;
    vector<long long> zero(n, 0);
    for (auto &ord : orders) {
        Solution s = greedy_fill_order(ord, zero);
        candidates.push_back(s);
    }

    // Get the best candidate
    Solution best = candidates[0];
    for (auto &s : candidates) {
        if (s.value > best.value) best = s;
    }

    // Local improvement by small removals and refill
    auto improve = [&](Solution sol)->Solution {
        // Use first-improvement hill climbing with small removals
        const int MAX_PASS = 3;
        for (int pass = 0; pass < MAX_PASS; ++pass) {
            bool improved = false;
            for (int i = 0; i < n && !improved; ++i) {
                if (sol.x[i] <= 0) continue;
                long long maxD = min(8LL, sol.x[i]);
                for (long long d = 1; d <= maxD && !improved; ++d) {
                    vector<long long> x2 = sol.x;
                    x2[i] -= d;
                    long long mass2 = sol.mass - d * m[i];
                    long long vol2 = sol.vol - d * l[i];
                    if (mass2 < 0 || vol2 < 0) continue; // shouldn't happen
                    // Try refilling using several orders
                    for (auto &ord : orders) {
                        Solution s3 = greedy_fill_order(ord, x2);
                        if (s3.value > sol.value) {
                            sol = s3;
                            improved = true;
                            break;
                        }
                    }
                }
            }
            if (!improved) break;
        }
        return sol;
    };

    best = improve(best);

    // Output result JSON with same keys order
    cout << "{\n";
    for (int i = 0; i < n; ++i) {
        long long chosen = 0;
        if (i < (int)best.x.size()) chosen = best.x[i];
        if (chosen < 0) chosen = 0;
        if (chosen > q[i]) chosen = q[i];
        cout << " \"" << names[i] << "\": " << chosen;
        if (i + 1 < n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";

    return 0;
}