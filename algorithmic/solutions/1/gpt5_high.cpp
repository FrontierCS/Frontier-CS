#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
    long long limit; // min(q, floor(M/m), floor(L/l))
};

struct Parser {
    string s;
    size_t i = 0;

    Parser(const string& str) : s(str), i(0) {}

    void skip() {
        while (i < s.size() && (s[i] == ' ' || s[i] == '\n' || s[i] == '\r' || s[i] == '\t')) i++;
    }

    bool match(char c) {
        skip();
        if (i < s.size() && s[i] == c) { i++; return true; }
        return false;
    }

    void expect(char c) {
        skip();
        if (i >= s.size() || s[i] != c) {
            // Simple fallback for invalid input; attempt to proceed.
            // In contest setting, input should be valid JSON as per spec.
        } else {
            i++;
        }
    }

    string parseString() {
        skip();
        string out;
        if (i < s.size() && s[i] == '"') {
            i++;
            while (i < s.size()) {
                char c = s[i++];
                if (c == '\\') {
                    if (i < s.size()) {
                        char next = s[i++];
                        // Handle only basic escapes
                        if (next == '"' || next == '\\' || next == '/') out.push_back(next);
                        else if (next == 'b') out.push_back('\b');
                        else if (next == 'f') out.push_back('\f');
                        else if (next == 'n') out.push_back('\n');
                        else if (next == 'r') out.push_back('\r');
                        else if (next == 't') out.push_back('\t');
                        else out.push_back(next);
                    }
                } else if (c == '"') {
                    break;
                } else {
                    out.push_back(c);
                }
            }
        }
        return out;
    }

    long long parseNumber() {
        skip();
        long long sign = 1;
        if (i < s.size() && s[i] == '-') { sign = -1; i++; }
        long long num = 0;
        bool hasDigits = false;
        while (i < s.size() && isdigit(static_cast<unsigned char>(s[i]))) {
            hasDigits = true;
            num = num * 10 + (s[i] - '0');
            i++;
        }
        if (!hasDigits) {
            // Invalid number per JSON spec; but inputs guarantee valid integers
        }
        return sign * num;
    }

    vector<Item> parseItems() {
        vector<Item> items;
        expect('{');
        while (true) {
            skip();
            if (i < s.size() && s[i] == '}') { i++; break; }
            string key = parseString();
            skip();
            expect(':');
            skip();
            expect('[');
            long long arr[4];
            for (int k = 0; k < 4; k++) {
                arr[k] = parseNumber();
                skip();
                if (k < 3) {
                    if (i < s.size() && s[i] == ',') i++;
                }
                skip();
            }
            expect(']');
            skip();
            if (i < s.size() && s[i] == ',') { i++; }
            Item it;
            it.name = key;
            it.q = arr[0];
            it.v = arr[1];
            it.m = arr[2];
            it.l = arr[3];
            it.limit = 0; // to be computed later
            items.push_back(it);
        }
        return items;
    }
};

static const long long CAP_M = 20000000LL; // 20 kg in mg
static const long long CAP_L = 25000000LL; // 25 L in µL

struct Solution {
    vector<long long> cnt;
    long long value;
};

long long compute_value(const vector<Item>& items, const vector<long long>& cnt) {
    long long V = 0;
    for (size_t i = 0; i < items.size(); i++) {
        V += cnt[i] * items[i].v;
    }
    return V;
}

void compute_usage(const vector<Item>& items, const vector<long long>& cnt, long long &usedM, long long &usedL) {
    usedM = 0; usedL = 0;
    for (size_t i = 0; i < items.size(); i++) {
        usedM += cnt[i] * items[i].m;
        usedL += cnt[i] * items[i].l;
    }
}

Solution greedy_run(const vector<Item>& items, int mode, double gamma) {
    int n = (int)items.size();
    vector<long long> cnt(n, 0);
    long long remM = CAP_M, remL = CAP_L;

    // Pre-calc available types
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    while (true) {
        int best = -1;
        long double bestScore = -1.0L;
        for (int i = 0; i < n; i++) {
            if (cnt[i] >= items[i].limit) continue;
            if (items[i].m > remM || items[i].l > remL) continue;

            long double denom = 0.0L;
            if (mode == 0) {
                denom = (long double)items[i].m / (long double)remM + (long double)items[i].l / (long double)remL;
            } else if (mode == 1) {
                long double a = (long double)items[i].m / (long double)remM;
                long double b = (long double)items[i].l / (long double)remL;
                denom = (a > b ? a : b);
            } else if (mode == 2) {
                denom = gamma * ((long double)items[i].m / (long double)remM) + (1.0L - gamma) * ((long double)items[i].l / (long double)remL);
            } else if (mode == 3) {
                denom = gamma * ((long double)items[i].m / (long double)CAP_M) + (1.0L - gamma) * ((long double)items[i].l / (long double)CAP_L);
            } else {
                denom = (long double)items[i].m / (long double)remM + (long double)items[i].l / (long double)remL;
            }
            if (denom <= 0.0L) continue;
            long double score = (long double)items[i].v / denom;
            if (score > bestScore) {
                bestScore = score;
                best = i;
            }
        }
        if (best == -1) break;
        cnt[best]++;
        remM -= items[best].m;
        remL -= items[best].l;
    }

    Solution sol;
    sol.cnt = cnt;
    sol.value = compute_value(items, cnt);
    return sol;
}

void pairwise_improve(const vector<Item>& items, vector<long long>& cnt) {
    int n = (int)items.size();
    long long usedM = 0, usedL = 0;
    compute_usage(items, cnt, usedM, usedL);
    long long remM = CAP_M - usedM;
    long long remL = CAP_L - usedL;

    bool improved = true;
    int iter = 0;
    while (improved && iter < 200) {
        improved = false;
        iter++;
        for (int i = 0; i < n; i++) {
            if (cnt[i] <= 0) continue;
            int maxT = (int)min<long long>(cnt[i], 3);
            for (int t = 1; t <= maxT; t++) {
                long long freeM = items[i].m * (long long)t;
                long long freeL = items[i].l * (long long)t;
                for (int j = 0; j < n; j++) {
                    if (i == j) continue;
                    long long avail_j = items[j].limit - cnt[j];
                    if (avail_j <= 0) continue;
                    long long kM = (items[j].m > 0 ? (remM + freeM) / items[j].m : LLONG_MAX);
                    long long kL = (items[j].l > 0 ? (remL + freeL) / items[j].l : LLONG_MAX);
                    long long k = min(avail_j, min(kM, kL));
                    if (k <= 0) continue;
                    long long gain = items[j].v * k - items[i].v * (long long)t;
                    if (gain > 0) {
                        // apply swap
                        cnt[i] -= t;
                        cnt[j] += k;
                        remM = remM + freeM - items[j].m * k;
                        remL = remL + freeL - items[j].l * k;
                        improved = true;
                        goto next_iteration;
                    }
                }
            }
        }
        next_iteration:
        if (improved) continue;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Read entire input
    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());

    Parser parser(input);
    vector<Item> items = parser.parseItems();

    // Compute per-item limit
    for (auto &it : items) {
        long long byM = (it.m > 0 ? CAP_M / it.m : (long long)1e18);
        long long byL = (it.l > 0 ? CAP_L / it.l : (long long)1e18);
        long long lim = min(it.q, min(byM, byL));
        if (lim < 0) lim = 0;
        it.limit = lim;
    }

    // Run multiple greedy variants
    vector<pair<int,double>> variants;
    variants.push_back({0, 0.0}); // residual sum
    variants.push_back({1, 0.0}); // residual max
    variants.push_back({2, 0.2});
    variants.push_back({2, 0.5});
    variants.push_back({2, 0.8});
    variants.push_back({3, 0.5}); // constant weighted

    Solution best;
    best.value = -1;
    best.cnt.assign(items.size(), 0);

    for (auto &var : variants) {
        Solution s = greedy_run(items, var.first, var.second);
        if (s.value > best.value) best = s;
    }

    // Local pairwise improvement
    pairwise_improve(items, best.cnt);

    // Ensure counts within limits and capacities (safety)
    for (size_t i = 0; i < items.size(); i++) {
        if (best.cnt[i] < 0) best.cnt[i] = 0;
        if (best.cnt[i] > items[i].limit) best.cnt[i] = items[i].limit;
    }
    // If somehow over capacity (shouldn't), greedily drop worst density until fits
    long long usedM, usedL;
    compute_usage(items, best.cnt, usedM, usedL);
    if (usedM > CAP_M || usedL > CAP_L) {
        // Drop items with lowest value per normalized usage until fits
        vector<int> idx(items.size());
        iota(idx.begin(), idx.end(), 0);
        auto cost_norm = [&](int i)->long double {
            return (long double)items[i].m / (long double)CAP_M + (long double)items[i].l / (long double)CAP_L;
        };
        while ((usedM > CAP_M || usedL > CAP_L)) {
            int worst = -1;
            long double worstScore = 1e300L;
            for (int i = 0; i < (int)items.size(); i++) {
                if (best.cnt[i] <= 0) continue;
                long double sc = (long double)items[i].v / (cost_norm(i));
                if (sc < worstScore) {
                    worstScore = sc;
                    worst = i;
                }
            }
            if (worst == -1) break;
            best.cnt[worst]--;
            usedM -= items[worst].m;
            usedL -= items[worst].l;
        }
    }

    // Output JSON with same keys order
    cout << "{\n";
    for (size_t i = 0; i < items.size(); i++) {
        cout << " \"" << items[i].name << "\": " << best.cnt[i];
        if (i + 1 != items.size()) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";
    return 0;
}