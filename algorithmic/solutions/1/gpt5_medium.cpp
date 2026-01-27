#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
    int idx;
};

struct Parser {
    string s;
    size_t pos = 0;
    Parser(const string &str): s(str), pos(0) {}
    void skip_ws() {
        while (pos < s.size() && isspace((unsigned char)s[pos])) pos++;
    }
    bool expect(char c) {
        skip_ws();
        if (pos < s.size() && s[pos] == c) { pos++; return true; }
        return false;
    }
    string read_string() {
        skip_ws();
        if (pos >= s.size() || s[pos] != '"') return "";
        pos++;
        string res;
        while (pos < s.size()) {
            char c = s[pos++];
            if (c == '"') break;
            // Assuming no escape sequences needed per problem statement (lowercase ascii keys)
            res.push_back(c);
        }
        return res;
    }
    long long read_ll() {
        skip_ws();
        long long sign = 1;
        if (pos < s.size() && (s[pos] == '+' || s[pos] == '-')) {
            if (s[pos] == '-') sign = -1;
            pos++;
        }
        long long num = 0;
        while (pos < s.size() && isdigit((unsigned char)s[pos])) {
            num = num * 10 + (s[pos] - '0');
            pos++;
        }
        return num * sign;
    }
    vector<long long> read_array_numbers() {
        vector<long long> nums;
        skip_ws();
        if (!expect('[')) return nums;
        while (true) {
            skip_ws();
            // If closing bracket immediately, break
            if (pos < s.size() && s[pos] == ']') {
                pos++;
                break;
            }
            long long val = read_ll();
            nums.push_back(val);
            skip_ws();
            if (pos < s.size() && s[pos] == ',') {
                pos++;
                continue;
            } else if (pos < s.size() && s[pos] == ']') {
                pos++;
                break;
            } else {
                // Unexpected, try to continue
                break;
            }
        }
        return nums;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire stdin into a string
    std::ostringstream oss;
    oss << cin.rdbuf();
    string input = oss.str();

    Parser p(input);
    const long long CAP_M = 20LL * 1000 * 1000; // mg
    const long long CAP_L = 25LL * 1000 * 1000; // uL

    vector<Item> items;
    vector<string> order_names;

    p.skip_ws();
    if (!p.expect('{')) {
        // Fallback: empty output
        cout << "{\n}\n";
        return 0;
    }
    while (true) {
        p.skip_ws();
        if (p.pos < input.size() && input[p.pos] == '}') { p.pos++; break; }
        string key = p.read_string();
        if (key.empty()) break;
        order_names.push_back(key);
        p.skip_ws();
        p.expect(':');
        vector<long long> arr = p.read_array_numbers(); // expects 4 numbers
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
        it.idx = (int)items.size();
        items.push_back(it);
        p.skip_ws();
        if (p.pos < input.size() && input[p.pos] == ',') {
            p.pos++;
            continue;
        } else if (p.pos < input.size() && input[p.pos] == '}') {
            p.pos++;
            break;
        } else {
            // continue attempting
            continue;
        }
    }

    int n = (int)items.size();
    if (n == 0) {
        cout << "{\n";
        // no items
        for (size_t i = 0; i < order_names.size(); ++i) {
            cout << (i == 0 ? " " : ", ") << "\"" << order_names[i] << "\": 0\n";
        }
        cout << "}\n";
        return 0;
    }

    // Cap per-item max by capacity feasibility
    vector<long long> maxFeasible(n);
    for (int i = 0; i < n; ++i) {
        long long byM = items[i].m > 0 ? (CAP_M / items[i].m) : 0;
        long long byL = items[i].l > 0 ? (CAP_L / items[i].l) : 0;
        long long mf = min(items[i].q, min(byM, byL));
        if (mf < 0) mf = 0;
        maxFeasible[i] = mf;
    }

    auto greedy_fill_with_order = [&](const vector<int>& ord,
                                      const vector<long long>& baseCounts,
                                      long long usedM, long long usedL) {
        vector<long long> x = baseCounts;
        long long remM = CAP_M - usedM;
        long long remL = CAP_L - usedL;
        long long val = 0;
        for (int i = 0; i < n; ++i) {
            if (x[i] < 0) x[i] = 0;
            if (x[i] > maxFeasible[i]) x[i] = maxFeasible[i];
            val += x[i] * items[i].v;
        }
        for (int idx : ord) {
            if (items[idx].m == 0 || items[idx].l == 0) continue; // per statement, shouldn't happen
            long long canq = maxFeasible[idx] - x[idx];
            if (canq <= 0) continue;
            long long cm = remM / items[idx].m;
            long long cl = remL / items[idx].l;
            long long can = min(canq, min(cm, cl));
            if (can <= 0) continue;
            x[idx] += can;
            remM -= can * items[idx].m;
            remL -= can * items[idx].l;
            val += can * items[idx].v;
            if (remM <= 0 || remL <= 0) break;
        }
        return pair<vector<long long>, long long>(x, val);
    };

    auto greedy_fill = [&](const vector<int>& ord) {
        vector<long long> base(n, 0);
        return greedy_fill_with_order(ord, base, 0, 0);
    };

    auto build_order_by_w = [&](double w) {
        vector<pair<double,int>> dens;
        dens.reserve(n);
        for (int i = 0; i < n; ++i) {
            // Normalize by capacities to make scales comparable
            double denom = w * (double)items[i].m / (double)CAP_M + (1.0 - w) * (double)items[i].l / (double)CAP_L;
            if (denom <= 0) denom = 1e-18;
            double score = (double)items[i].v / denom;
            dens.emplace_back(score, i);
        }
        sort(dens.begin(), dens.end(), [&](const auto& a, const auto& b){
            if (a.first != b.first) return a.first > b.first;
            // tie-breakers: higher value then lower size
            if (items[a.second].v != items[b.second].v) return items[a.second].v > items[b.second].v;
            long long sa = items[a.second].m + items[a.second].l;
            long long sb = items[b.second].m + items[b.second].l;
            if (sa != sb) return sa < sb;
            return a.second < b.second;
        });
        vector<int> ord;
        ord.reserve(n);
        for (auto &pr : dens) ord.push_back(pr.second);
        return ord;
    };

    auto build_order_by_custom_desc = [&](const vector<double>& score) {
        vector<int> ord(n);
        iota(ord.begin(), ord.end(), 0);
        sort(ord.begin(), ord.end(), [&](int a, int b){
            if (score[a] != score[b]) return score[a] > score[b];
            if (items[a].v != items[b].v) return items[a].v > items[b].v;
            long long sa = items[a].m + items[a].l;
            long long sb = items[b].m + items[b].l;
            if (sa != sb) return sa < sb;
            return a < b;
        });
        return ord;
    };
    auto build_order_small_size_first = [&]() {
        vector<pair<double,int>> arr;
        arr.reserve(n);
        for (int i = 0; i < n; ++i) {
            double s = (double)items[i].m / (double)CAP_M + (double)items[i].l / (double)CAP_L;
            arr.emplace_back(s, i);
        }
        sort(arr.begin(), arr.end(), [&](const auto& a, const auto& b){
            if (a.first != b.first) return a.first < b.first;
            if (items[a.second].v != items[b.second].v) return items[a.second].v > items[b.second].v;
            return a.second < b.second;
        });
        vector<int> ord;
        for (auto &pr : arr) ord.push_back(pr.second);
        return ord;
    };

    vector<vector<int>> orders;

    auto add_order_if_new = [&](const vector<int>& ord) {
        for (auto &o : orders) {
            if (o == ord) return;
        }
        orders.push_back(ord);
    };

    // Various heuristic orders
    vector<double> ws = {0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0};
    for (double w : ws) add_order_if_new(build_order_by_w(w));

    // value per max(m/M, l/L)
    {
        vector<double> sc(n);
        for (int i = 0; i < n; ++i) {
            double denom = max((double)items[i].m / (double)CAP_M, (double)items[i].l / (double)CAP_L);
            if (denom <= 0) denom = 1e-18;
            sc[i] = (double)items[i].v / denom;
        }
        add_order_if_new(build_order_by_custom_desc(sc));
    }
    // value per mass (same as w=1 but include anyway due to tiebreak)
    {
        vector<double> sc(n);
        for (int i = 0; i < n; ++i) {
            double denom = (double)items[i].m / (double)CAP_M;
            if (denom <= 0) denom = 1e-18;
            sc[i] = (double)items[i].v / denom;
        }
        add_order_if_new(build_order_by_custom_desc(sc));
    }
    // value per volume (w=0)
    {
        vector<double> sc(n);
        for (int i = 0; i < n; ++i) {
            double denom = (double)items[i].l / (double)CAP_L;
            if (denom <= 0) denom = 1e-18;
            sc[i] = (double)items[i].v / denom;
        }
        add_order_if_new(build_order_by_custom_desc(sc));
    }
    // pure value
    {
        vector<double> sc(n);
        for (int i = 0; i < n; ++i) sc[i] = (double)items[i].v;
        add_order_if_new(build_order_by_custom_desc(sc));
    }
    // small size first
    add_order_if_new(build_order_small_size_first());

    // Initial solutions via greedy on multiple orders
    vector<long long> bestX(n, 0);
    long long bestV = 0;
    long long bestUsedM = 0, bestUsedL = 0;
    vector<int> bestOrd;
    for (auto &ord : orders) {
        auto res = greedy_fill(ord);
        auto &x = res.first;
        long long v = res.second;
        if (v > bestV) {
            bestV = v;
            bestX = x;
            long long usedM = 0, usedL = 0;
            for (int i = 0; i < n; ++i) {
                usedM += x[i] * items[i].m;
                usedL += x[i] * items[i].l;
            }
            bestUsedM = usedM;
            bestUsedL = usedL;
            bestOrd = ord;
        }
    }

    // Local improvement: hill climbing via remove-then-refill
    auto start = chrono::steady_clock::now();
    auto elapsed_ms = [&]() {
        return chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - start).count();
    };

    auto build_dynamic_order = [&](long long usedM, long long usedL) {
        double um = (double)usedM / (double)CAP_M;
        double ul = (double)usedL / (double)CAP_L;
        double denom = um + ul;
        double w = 0.5;
        if (denom > 1e-12) {
            w = um / denom;
        }
        return build_order_by_w(w);
    };

    const long long time_limit_ms = 900; // keep some margin
    bool improved = true;
    while (improved && elapsed_ms() < time_limit_ms) {
        improved = false;
        for (int i = 0; i < n && elapsed_ms() < time_limit_ms; ++i) {
            if (bestX[i] <= 0) continue;
            long long max_remove = min<long long>(4, bestX[i]);
            for (long long r = 1; r <= max_remove && elapsed_ms() < time_limit_ms; ++r) {
                vector<long long> curX = bestX;
                curX[i] -= r;
                long long curUsedM = bestUsedM - r * items[i].m;
                long long curUsedL = bestUsedL - r * items[i].l;
                long long curV = bestV - r * items[i].v;
                if (curUsedM < 0) curUsedM = 0; // safety
                if (curUsedL < 0) curUsedL = 0;

                vector<int> dynOrd = build_dynamic_order(curUsedM, curUsedL);

                // Try dynamic order, then fallback to bestOrd
                bool found = false;
                for (int attempt = 0; attempt < 2; ++attempt) {
                    const vector<int>& ord = (attempt == 0 ? dynOrd : bestOrd.size() ? bestOrd : dynOrd);
                    auto res = greedy_fill_with_order(ord, curX, curUsedM, curUsedL);
                    auto &x2 = res.first;
                    long long v2 = res.second;
                    if (v2 > bestV) {
                        // accept
                        bestX = x2;
                        bestV = v2;
                        long long uM = 0, uL = 0;
                        for (int k = 0; k < n; ++k) {
                            uM += bestX[k] * items[k].m;
                            uL += bestX[k] * items[k].l;
                        }
                        bestUsedM = uM;
                        bestUsedL = uL;
                        improved = true;
                        found = true;
                        break;
                    }
                }
                if (found) break;
            }
            if (improved) break;
        }
    }

    // Ensure counts do not exceed q and fit capacities (safety trim if any numerical issues)
    for (int i = 0; i < n; ++i) {
        if (bestX[i] < 0) bestX[i] = 0;
        if (bestX[i] > items[i].q) bestX[i] = items[i].q;
    }
    // Hard trim in case of slight over-capacity (shouldn't happen)
    auto totalM = [&]() {
        long long s = 0; for (int i = 0; i < n; ++i) s += bestX[i] * items[i].m; return s;
    };
    auto totalL = [&]() {
        long long s = 0; for (int i = 0; i < n; ++i) s += bestX[i] * items[i].l; return s;
    };
    long long curM = totalM();
    long long curL = totalL();
    if (curM > CAP_M || curL > CAP_L) {
        // Remove from least efficient items until fits
        vector<int> ord = build_order_by_w(0.5);
        // reverse (least efficient last in ord) -> remove from end to start
        for (int idx = n - 1; idx >= 0 && (curM > CAP_M || curL > CAP_L); --idx) {
            int i = ord[idx];
            while (bestX[i] > 0 && (curM > CAP_M || curL > CAP_L)) {
                bestX[i]--;
                curM -= items[i].m;
                curL -= items[i].l;
            }
        }
    }

    // Output JSON with same keys as input (in original order)
    // Map names to counts (by index), ensure using input order_names
    unordered_map<string, long long> name_to_count;
    name_to_count.reserve(n * 2);
    for (int i = 0; i < n; ++i) {
        name_to_count[items[i].name] = bestX[i];
    }
    cout << "{\n";
    for (size_t i = 0; i < order_names.size(); ++i) {
        const string &nm = order_names[i];
        long long cnt = 0;
        auto it = name_to_count.find(nm);
        if (it != name_to_count.end()) cnt = it->second;
        cout << (i == 0 ? " " : ", ") << "\"" << nm << "\": " << cnt << "\n";
    }
    cout << "}\n";

    return 0;
}