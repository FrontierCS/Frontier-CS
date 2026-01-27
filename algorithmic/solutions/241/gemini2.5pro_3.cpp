#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <map>
#include <unordered_map>
#include <queue>

using namespace std;

const int ULL_BITS = 64;

struct TruthTable {
    int n;
    vector<unsigned long long> bits;

    TruthTable(int n_val) : n(n_val) {
        bits.resize(((1 << n) + ULL_BITS - 1) / ULL_BITS, 0);
    }
    
    TruthTable(int n_val, const string& s) : n(n_val) {
        bits.resize(((1 << n) + ULL_BITS - 1) / ULL_BITS, 0);
        for (int i = 0; i < (1 << n); ++i) {
            if (s[i] == '1') {
                bits[i / ULL_BITS] |= (1ULL << (i % ULL_BITS));
            }
        }
    }

    bool operator<(const TruthTable& other) const {
        return bits < other.bits;
    }
    bool operator==(const TruthTable& other) const {
        return bits == other.bits;
    }
};

struct TruthTableHasher {
    size_t operator()(const TruthTable& tt) const {
        size_t h = 0;
        for (unsigned long long val : tt.bits) {
            h ^= hash<unsigned long long>{}(val) + 0x9e3779b9 + (h << 6) + (h >> 2);
        }
        return h;
    }
};

TruthTable op_or(const TruthTable& t1, const TruthTable& t2) {
    TruthTable res(t1.n);
    for (size_t i = 0; i < t1.bits.size(); ++i) {
        res.bits[i] = t1.bits[i] | t2.bits[i];
    }
    return res;
}

TruthTable op_and(const TruthTable& t1, const TruthTable& t2) {
    TruthTable res(t1.n);
    for (size_t i = 0; i < t1.bits.size(); ++i) {
        res.bits[i] = t1.bits[i] & t2.bits[i];
    }
    return res;
}

bool is_monotone(int n, const string& s) {
    for (int i = 0; i < (1 << n); ++i) {
        for (int j = 0; j < n; ++j) {
            if (!((i >> j) & 1)) {
                int i_prime = i | (1 << j);
                if (s[i] > s[i_prime]) {
                    return false;
                }
            }
        }
    }
    return true;
}

pair<int, string> build_or(const string& e1, int c1, const string& e2, int c2) {
    if (e1 == "F") return {c2, e2};
    if (e2 == "F") return {c1, e1};
    if (e1 == "T" || e2 == "T") return {0, "T"};
    if (e1 == e2) return {c1, e1};
    string s1 = e1, s2 = e2;
    if (s1 > s2) swap(s1, s2);
    return {c1 + c2 + 1, "(" + s1 + "|" + s2 + ")"};
}

pair<int, string> build_and(const string& e1, int c1, const string& e2, int c2) {
    if (e1 == "F" || e2 == "F") return {0, "F"};
    if (e1 == "T") return {c2, e2};
    if (e2 == "T") return {c1, e1};
    if (e1 == e2) return {c1, e1};
    string s1 = e1, s2 = e2;
    if (s1 > s2) swap(s1, s2);
    return {c1 + c2 + 1, "(" + s1 + "&" + s2 + ")"};
}

void solve_case() {
    int n;
    cin >> n;
    string s;
    cin >> s;

    if (!is_monotone(n, s)) {
        cout << "No\n";
        return;
    }

    unordered_map<TruthTable, int, TruthTableHasher> dist;
    unordered_map<TruthTable, string, TruthTableHasher> expr_map;
    priority_queue<pair<int, TruthTable>, vector<pair<int, TruthTable>>, greater<pair<int, TruthTable>>> pq;
    
    TruthTable target_tt(n, s);

    string s_F_str(1 << n, '0');
    TruthTable tt_F(n, s_F_str);
    dist[tt_F] = 0;
    expr_map[tt_F] = "F";
    pq.push({0, tt_F});

    string s_T_str(1 << n, '1');
    TruthTable tt_T(n, s_T_str);
    if (dist.find(tt_T) == dist.end()) {
        dist[tt_T] = 0;
        expr_map[tt_T] = "T";
        pq.push({0, tt_T});
    }

    for (int i = 0; i < n; ++i) {
        string s_var(1 << n, '0');
        for (int j = 0; j < (1 << n); ++j) {
            if ((j >> i) & 1) s_var[j] = '1';
        }
        TruthTable tt_var(n, s_var);
        if (dist.find(tt_var) == dist.end()) {
            dist[tt_var] = 0;
            expr_map[tt_var] = string(1, 'a' + i);
            pq.push({0, tt_var});
        }
    }
    
    vector<TruthTable> finalized_tts;
    string final_expr = "";

    while (!pq.empty()) {
        auto [d, u_tt] = pq.top();
        pq.pop();

        if (dist.count(u_tt) && d > dist.at(u_tt)) {
            continue;
        }

        if (u_tt == target_tt) {
            final_expr = expr_map.at(u_tt);
            break;
        }
        
        finalized_tts.push_back(u_tt);
        string u_e = expr_map.at(u_tt);

        for (const auto& v_tt : finalized_tts) {
            int v_c = dist.at(v_tt);
            string v_e = expr_map.at(v_tt);

            // OR
            TruthTable or_tt = op_or(u_tt, v_tt);
            auto or_res = build_or(u_e, d, v_e, v_c);
            if (!dist.count(or_tt) || or_res.first < dist.at(or_tt)) {
                dist[or_tt] = or_res.first;
                expr_map[or_tt] = or_res.second;
                pq.push({dist[or_tt], or_tt});
            }

            // AND
            TruthTable and_tt = op_and(u_tt, v_tt);
            auto and_res = build_and(u_e, d, v_e, v_c);
            if (!dist.count(and_tt) || and_res.first < dist.at(and_tt)) {
                dist[and_tt] = and_res.first;
                expr_map[and_tt] = and_res.second;
                pq.push({dist[and_tt], and_tt});
            }
        }
    }

    cout << "Yes\n";
    cout << final_expr << "\n";
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve_case();
    }
    return 0;
}