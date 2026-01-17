#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n, m;
    cin >> n >> m;
    vector<array<int,3>> clauses(m);
    vector<vector<int>> pos_clauses(n+1), neg_clauses(n+1);
    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        auto process = [&](int lit) {
            int var = abs(lit);
            if (lit > 0) {
                pos_clauses[var].push_back(i);
            } else {
                neg_clauses[var].push_back(i);
            }
        };
        process(a);
        process(b);
        process(c);
    }
    
    if (m == 0) {
        for (int i = 0; i < n; i++) {
            cout << 0 << " \n"[i==n-1];
        }
        return 0;
    }
    
    random_device rd;
    mt19937 gen(rd());
    uniform_real_distribution<double> prob(0.0, 1.0);
    uniform_int_distribution<int> var_dist(1, n);
    
    vector<bool> assign(n+1);
    for (int i = 1; i <= n; i++) {
        assign[i] = gen() % 2;
    }
    
    vector<int> sat_count(m, 0);
    int total_sat = 0;
    for (int i = 0; i < m; i++) {
        for (int lit : clauses[i]) {
            int var = abs(lit);
            bool sign = (lit > 0);
            if (assign[var] == sign) {
                sat_count[i]++;
            }
        }
        if (sat_count[i] >= 1) total_sat++;
    }
    
    double T = 10.0;
    const double T_min = 1e-9;
    const double alpha = 0.9999;
    int max_iter = 200000;
    int iter = 0;
    
    int best_total = total_sat;
    vector<bool> best_assign = assign;
    
    while (T > T_min && iter < max_iter) {
        iter++;
        int v = var_dist(gen);
        
        int delta = 0;
        for (int c : pos_clauses[v]) {
            bool old_sat = (sat_count[c] >= 1);
            bool new_sat;
            if (assign[v]) {
                new_sat = (sat_count[c] - 1 >= 1);
            } else {
                new_sat = (sat_count[c] + 1 >= 1);
            }
            if (old_sat && !new_sat) delta--;
            if (!old_sat && new_sat) delta++;
        }
        for (int c : neg_clauses[v]) {
            bool old_sat = (sat_count[c] >= 1);
            bool new_sat;
            if (assign[v]) {
                new_sat = (sat_count[c] + 1 >= 1);
            } else {
                new_sat = (sat_count[c] - 1 >= 1);
            }
            if (old_sat && !new_sat) delta--;
            if (!old_sat && new_sat) delta++;
        }
        
        if (delta > 0 || prob(gen) < exp(delta / T)) {
            for (int c : pos_clauses[v]) {
                if (assign[v]) {
                    sat_count[c]--;
                } else {
                    sat_count[c]++;
                }
            }
            for (int c : neg_clauses[v]) {
                if (assign[v]) {
                    sat_count[c]++;
                } else {
                    sat_count[c]--;
                }
            }
            assign[v] = !assign[v];
            total_sat += delta;
            if (total_sat > best_total) {
                best_total = total_sat;
                best_assign = assign;
            }
        }
        
        T *= alpha;
    }
    
    assign = best_assign;
    fill(sat_count.begin(), sat_count.end(), 0);
    total_sat = 0;
    for (int i = 0; i < m; i++) {
        for (int lit : clauses[i]) {
            int var = abs(lit);
            bool sign = (lit > 0);
            if (assign[var] == sign) {
                sat_count[i]++;
            }
        }
        if (sat_count[i] >= 1) total_sat++;
    }
    
    bool improved = true;
    while (improved) {
        improved = false;
        vector<int> vars(n);
        iota(vars.begin(), vars.end(), 1);
        shuffle(vars.begin(), vars.end(), gen);
        for (int v : vars) {
            int delta = 0;
            for (int c : pos_clauses[v]) {
                bool old_sat = (sat_count[c] >= 1);
                bool new_sat;
                if (assign[v]) {
                    new_sat = (sat_count[c] - 1 >= 1);
                } else {
                    new_sat = (sat_count[c] + 1 >= 1);
                }
                if (old_sat && !new_sat) delta--;
                if (!old_sat && new_sat) delta++;
            }
            for (int c : neg_clauses[v]) {
                bool old_sat = (sat_count[c] >= 1);
                bool new_sat;
                if (assign[v]) {
                    new_sat = (sat_count[c] + 1 >= 1);
                } else {
                    new_sat = (sat_count[c] - 1 >= 1);
                }
                if (old_sat && !new_sat) delta--;
                if (!old_sat && new_sat) delta++;
            }
            if (delta > 0) {
                for (int c : pos_clauses[v]) {
                    if (assign[v]) {
                        sat_count[c]--;
                    } else {
                        sat_count[c]++;
                    }
                }
                for (int c : neg_clauses[v]) {
                    if (assign[v]) {
                        sat_count[c]++;
                    } else {
                        sat_count[c]--;
                    }
                }
                assign[v] = !assign[v];
                total_sat += delta;
                improved = true;
            }
        }
    }
    
    for (int i = 1; i <= n; i++) {
        cout << (assign[i] ? 1 : 0) << " \n"[i==n];
    }
    
    return 0;
}