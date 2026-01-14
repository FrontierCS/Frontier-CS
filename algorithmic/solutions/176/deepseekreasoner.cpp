#include <iostream>
#include <vector>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <algorithm>
#include <random>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);
    
    int n, m;
    cin >> n >> m;
    
    if (m == 0) {
        for (int i = 0; i < n; i++) {
            if (i > 0) cout << " ";
            cout << 0;
        }
        cout << "\n";
        return 0;
    }
    
    vector<vector<pair<int, bool>>> clauses(m);
    vector<vector<pair<int, bool>>> var_clauses(n);
    
    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        auto process = [&](int x) {
            int var = abs(x) - 1;
            bool is_pos = (x > 0);
            clauses[i].push_back({var, is_pos});
            var_clauses[var].push_back({i, is_pos});
        };
        process(a);
        process(b);
        process(c);
    }
    
    vector<int> assign(n, 0);
    for (int v = 0; v < n; v++) {
        int bias = 0;
        for (auto &p : var_clauses[v]) {
            if (p.second) bias++;
            else bias--;
        }
        assign[v] = (bias >= 0) ? 1 : 0;
    }
    
    vector<int> true_count(m, 0);
    int satisfied = 0;
    for (int i = 0; i < m; i++) {
        for (auto &lit : clauses[i]) {
            int v = lit.first;
            bool pos = lit.second;
            if (assign[v] == pos) true_count[i]++;
        }
        if (true_count[i] > 0) satisfied++;
    }
    
    vector<int> best_assign = assign;
    int best_satisfied = satisfied;
    
    mt19937 rng(time(0));
    uniform_real_distribution<double> dist(0.0, 1.0);
    
    double T_start = 1.0;
    double T_end = 1e-4;
    int iterations = 200000;
    double cooling = pow(T_end / T_start, 1.0 / iterations);
    double T = T_start;
    
    for (int iter = 0; iter < iterations; iter++) {
        int v = rng() % n;
        int old_val = assign[v];
        int delta = 0;
        
        for (auto &cl : var_clauses[v]) {
            int c = cl.first;
            bool pos = cl.second;
            bool lit_truth = (old_val == pos);
            int old_true = true_count[c];
            int new_true = old_true + (lit_truth ? -1 : 1);
            bool old_sat = (old_true > 0);
            bool new_sat = (new_true > 0);
            delta += (new_sat - old_sat);
        }
        
        if (delta > 0 || dist(rng) < exp(delta / T)) {
            assign[v] = 1 - old_val;
            satisfied += delta;
            for (auto &cl : var_clauses[v]) {
                int c = cl.first;
                bool pos = cl.second;
                bool old_lit = (old_val == pos);
                if (old_lit) true_count[c]--;
                else true_count[c]++;
            }
            if (satisfied > best_satisfied) {
                best_satisfied = satisfied;
                best_assign = assign;
            }
        }
        T *= cooling;
    }
    
    for (int i = 0; i < n; i++) {
        if (i > 0) cout << " ";
        cout << best_assign[i];
    }
    cout << "\n";
    
    return 0;
}