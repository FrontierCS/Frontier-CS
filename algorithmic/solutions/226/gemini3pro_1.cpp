#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

typedef long long ll;

// Function to calculate GCD of two numbers
ll gcd(ll a, ll b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

// Solves Maximum Independent Set on a linear path with node weights
// DP state: dp0 = max weight without picking current, dp1 = max weight picking current
ll solve_linear(const vector<ll>& w) {
    if (w.empty()) return 0;
    ll dp0 = 0;          // Max weight ending at i-1, i not picked
    ll dp1 = w[0];       // Max weight ending at i-1, i picked
    for (size_t i = 1; i < w.size(); ++i) {
        ll new_dp0 = max(dp0, dp1);
        ll new_dp1 = dp0 + w[i];
        dp0 = new_dp0;
        dp1 = new_dp1;
    }
    return max(dp0, dp1);
}

// Solves Maximum Independent Set on a cycle with node weights
ll solve_cycle(const vector<ll>& w) {
    if (w.empty()) return 0;
    if (w.size() == 1) return w[0];
    
    // Case 1: Node 0 is not picked. Problem reduces to linear path 1..K-1
    vector<ll> w1(w.begin() + 1, w.end());
    ll ans1 = solve_linear(w1);
    
    // Case 2: Node 0 is picked. Nodes 1 and K-1 cannot be picked.
    // Problem reduces to linear path 2..K-2 plus weight of 0.
    ll ans2 = 0;
    if (w.size() > 3) {
        vector<ll> w2(w.begin() + 2, w.end() - 1);
        ans2 = solve_linear(w2);
    } else if (w.size() == 3) {
        // Only node 0 is picked (1 and 2 blocked)
        ans2 = 0;
    }
    ans2 += w[0];
    
    return max(ans1, ans2);
}

// Global vector to avoid frequent reallocations
vector<ll> weights;

// Solves for a specific component size M on a cycle of length K
// xp is the step size in the cycle: node u corresponds to original residue (u * xp) % K
ll solve_component(ll M, ll K, ll xp) {
    if (M == 0) return 0;
    ll q = M / K;
    ll rem = M % K;
    
    if (weights.size() != static_cast<size_t>(K)) weights.resize(K);
    
    // Fill weights based on the mapping u -> (u * xp) % K
    // The original residue r = (u * xp) % K determines the size of the class.
    // If r < rem, the count is q + 1, otherwise q.
    // We iterate u from 0 to K-1 to build the cycle weights in order.
    
    ll curr = 0; // corresponds to (u * xp) % K for u=0
    // Note: Since K = x' + y' and xp = x', gcd(xp, K) = gcd(x', x'+y') = gcd(x', y') = 1.
    // So this loop visits all residues exactly once, but we need the order on the cycle 0..K-1.
    
    for (int u = 0; u < K; ++u) {
        // curr is the original residue corresponding to node u in the transformed cycle
        if (curr < rem) weights[u] = q + 1;
        else weights[u] = q;
        
        curr += xp;
        if (curr >= K) curr -= K;
    }
    
    return solve_cycle(weights);
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    ll n, x, y;
    if (!(cin >> n >> x >> y)) return 0;
    
    ll g = gcd(x, y);
    ll xp = x / g;
    ll yp = y / g;
    ll K = xp + yp;
    
    // The problem decomposes into g independent components based on residues modulo g.
    // Within each component, we have a structure determined by K.
    // If K is even, the graph is bipartite.
    // If K is odd, the graph is a collection of odd cycles (homomorphic to C_K).
    
    if (K % 2 == 0) {
        // Bipartite case
        // The components are just paths. The optimal strategy is to pick every alternate node.
        // For a path of length L, max IS is ceil(L/2).
        
        ll Q = n / g;
        ll R = n % g;
        // There are R components of size Q+1 (residues 1..R)
        // There are g - R components of size Q (residues R+1..g)
        
        ll ans = 0;
        ans += R * ((Q + 2) / 2);      // ceil((Q+1)/2)
        ans += (g - R) * ((Q + 1) / 2); // ceil(Q/2)
        
        cout << ans << endl;
    } else {
        // Odd cycle case
        // The graph wraps around forming dependencies like a cycle of length K.
        // We solve the Maximum Weight Independent Set on C_K for each component type.
        
        ll Q_all = n / g;
        ll R_all = n % g;
        
        ll ans = 0;
        
        // R_all components have size Q_all + 1
        if (R_all > 0) {
            ans += R_all * solve_component(Q_all + 1, K, xp);
        }
        
        // g - R_all components have size Q_all
        if (g - R_all > 0) {
            ans += (g - R_all) * solve_component(Q_all, K, xp);
        }
        
        cout << ans << endl;
    }
    
    return 0;
}