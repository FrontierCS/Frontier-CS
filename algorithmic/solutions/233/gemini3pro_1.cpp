#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <map>

using namespace std;

// Global budget tracking
double MAX_TOTAL_COST = 490.0; // Slightly conservative to be safe
double current_total_cost = 0;

struct Candidate {
    int v;
    int r, c;
    double prob;
};

// Log binomial coefficients
double lbinom[1005][1005];

void precompute() {
    // Not strictly necessary to precompute array if using lgamma, but good for speed
}

double get_prob(int r, int c) {
    // 1-based r, c. Steps down = r-1, Steps right = c-1. Total steps K = r+c-2.
    int R = r - 1;
    int C = c - 1;
    int K = R + C;
    if (K == 0) return 1.0;
    // log prob = lbinom(K, R) - K * log(2)
    // lgamma(n) computes log((n-1)!)
    double lb = lgamma(K + 1) - lgamma(R + 1) - lgamma(C + 1);
    double lp = lb - K * log(2.0);
    return exp(lp);
}

void solve() {
    int n, m;
    if (!(cin >> n >> m)) return;
    vector<vector<int>> G(n + 1, vector<int>(n + 1));
    vector<pair<int, int>> pos(n * n + 1);
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            cin >> G[i][j];
            pos[G[i][j]] = {i, j};
        }
    }

    vector<int> answers;
    
    // Track visited (l=1, T) to avoid redundant queries/counts
    map<int, int> visited_l1;

    // 1. Calculate known values for T=1 and T=2 for all snakes l
    // These are "free" information (cost 0, no query needed)
    for (int l = 1; l <= n; l++) {
        // T=1: Snake is (1,1), (1,2), ..., (1,l)
        int mx1 = 0;
        for (int k = 1; k <= l && k <= n; k++) mx1 = max(mx1, G[1][k]);
        answers.push_back(mx1);
        
        // Mark for l=1
        if (l == 1) visited_l1[1] = mx1;

        // T=2: Snake is (2,1), (1,1), ..., (1, l-1)
        // First move is always down, so head is (2,1).
        if (l == 1) {
            // Length 1 snake at T=2 is just {(2,1)}
            if (n >= 2) {
                int val = G[2][1];
                answers.push_back(val);
                visited_l1[2] = val;
            }
        } else {
            // Length l >= 2. Head (2,1), Body (1,1)...(1, l-1)
            // (1,1)...(1,l-1) are the first l-1 cells of row 1.
            int mx2 = G[2][1]; // (2,1)
            for (int k = 1; k < l && k <= n; k++) mx2 = max(mx2, G[1][k]);
            answers.push_back(mx2);
        }
    }

    // 2. Identify candidates for l=1 queries
    // We want to find small values. Small values are likely found by querying f(1, T).
    // Heuristic: Iterate values v = 1, 2...
    // If v is at (r, c), snake 1 visits it at T = r+c-1.
    // We check probability of snake 1 visiting (r, c). If decent, we query.
    vector<Candidate> cands;
    int target_cands = max(m * 2, 2000); 
    
    for (int v = 1; v <= n * n; v++) {
        int r = pos[v].first;
        int c = pos[v].second;
        double p = get_prob(r, c);
        
        // Threshold tuning
        // For small N, p is high. For N=500, p is small (peak ~0.03).
        // We want to filter out extremely unlikely paths.
        double thresh = (n <= 30) ? 0.0 : 1e-4;
        
        if (p > thresh) {
            cands.push_back({v, r, c, p});
        } else if (v <= 50) { 
            // Force check very small values even if unlikely
            cands.push_back({v, r, c, p});
        }
        
        // Optimization: if we have collected enough candidates and passed m, stop
        if ((int)cands.size() > target_cands && v > m) break; 
    }
    
    // Candidates are added in increasing order of v, which is what we want.

    int queries_made = 0;
    int query_limit = 120 * n + m;
    
    for (const auto& cand : cands) {
        // Stop if we have plenty of answers or budget tight
        if ((int)answers.size() >= m + 200) break;
        if (current_total_cost >= MAX_TOTAL_COST) break;
        
        int T = cand.r + cand.c - 1;
        if (T < 1 || T > 2 * n - 1) continue;
        
        if (visited_l1.count(T)) continue;
        
        double cost = 1.05; // 0.05 + 1/1
        if (current_total_cost + cost > MAX_TOTAL_COST) break;
        if (queries_made >= query_limit - 10) break;

        cout << "? 1 " << T << endl;
        queries_made++;
        current_total_cost += cost;
        
        int res;
        cin >> res;
        answers.push_back(res);
        visited_l1[T] = res;
    }
    
    // 3. Fallback: If we still haven't found m values, perform cheap queries on large l
    // This is to satisfy the output count requirement.
    // Large l queries are cheap but likely return large values.
    int l_fill = n;
    int t_fill = 3;
    while ((int)answers.size() < m) {
        if (current_total_cost + 0.1 > MAX_TOTAL_COST) break; // Reserve slightly
        if (queries_made >= query_limit) break;
        
        // Check if we query l=n. Cost ~ 0.05
        cout << "? " << l_fill << " " << t_fill << endl;
        queries_made++;
        current_total_cost += (0.05 + 1.0/l_fill);
        
        int res;
        cin >> res;
        answers.push_back(res);
        
        t_fill++;
        if (t_fill > 2*n - 1) {
            t_fill = 3;
            l_fill--;
            if (l_fill < max(1, n/2)) l_fill = n; // Cycle back or stop
        }
    }
    
    // Final check to ensure we output m values
    while ((int)answers.size() < m) {
        answers.push_back(n*n);
    }
    
    sort(answers.begin(), answers.end());
    
    cout << "!";
    for (int i = 0; i < m; i++) {
        cout << " " << answers[i];
    }
    cout << endl;
}

int main() {
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}