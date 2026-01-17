#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

typedef long long ll;

ll gcd(ll a, ll b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

// Solves Maximum Weight Independent Set on a cycle with weights W using O(1) auxiliary space
// The graph is a cycle 0-1-2-...-(m-1)-0
ll solve_cycle(const vector<ll>& W) {
    int m = W.size();
    // Since x'+y' is odd and x',y' >= 1, m >= 3 always in the non-bipartite context.
    // Handling generic cases for robustness.
    if (m == 0) return 0;
    if (m == 1) return W[0];
    if (m == 2) return max(W[0], W[1]);

    // Case 1: Node 0 is NOT selected.
    // Solve linear MWIS for 1 to m-1
    // dp[i][0] corresponds to max weight for range ...i where i is not selected
    // dp[i][1] corresponds to max weight for range ...i where i is selected
    
    // Start at index 1
    ll prev0 = 0;       // dp[1][0]
    ll prev1 = W[1];    // dp[1][1]
    
    for (int i = 2; i < m; ++i) {
        ll curr0 = max(prev0, prev1);
        ll curr1 = prev0 + W[i];
        prev0 = curr0;
        prev1 = curr1;
    }
    ll ans1 = max(prev0, prev1);

    // Case 2: Node 0 IS selected.
    // Then 1 and m-1 cannot be selected.
    // Solve linear MWIS for 2 to m-2
    // Add W[0] to result.
    
    ll ans2 = 0;
    if (m == 3) {
        // Range 2..1 is empty. Just W[0].
        ans2 = W[0];
    } else {
        // Start at index 2
        prev0 = 0;      // dp[2][0]
        prev1 = W[2];   // dp[2][1]
        
        for (int i = 3; i <= m-2; ++i) {
            ll curr0 = max(prev0, prev1);
            ll curr1 = prev0 + W[i];
            prev0 = curr0;
            prev1 = curr1;
        }
        ans2 = W[0] + max(prev0, prev1);
    }
    
    return max(ans1, ans2);
}

ll solve_instance(ll n_len, ll x_prime, ll y_prime) {
    ll M = x_prime + y_prime;
    if (M == 0) return 0;
    
    ll base = n_len / M;
    ll rem = n_len % M;
    
    vector<ll> W(M);
    // Construct weights for each cluster in the cycle of clusters.
    // The clusters are indexed k=0..M-1.
    // The residue associated with cluster k is p_k = (k * x') % M.
    // The size of cluster k is (base + 1) if p_k < rem, else base.
    
    for (int k = 0; k < M; ++k) {
        ll p_k = ( (ll)k * x_prime ) % M;
        if (p_k < rem) W[k] = base + 1;
        else W[k] = base;
    }
    return solve_cycle(W);
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    ll n, x, y;
    if (cin >> n >> x >> y) {
        ll g = gcd(x, y);
        ll xp = x / g;
        ll yp = y / g;
        
        if ((xp + yp) % 2 == 0) {
            // Bipartite case
            // The graph decomposes into disjoint bipartite components.
            // For each residue modulo g, we have a sequence of length L.
            // The max independent set size for that sequence is ceil(L/2).
            ll q = n / g;
            ll r = n % g;
            ll ans = 0;
            
            // There are r sequences of length q+1
            if (r > 0) {
                ans += r * ((q + 2) / 2);
            }
            // There are g-r sequences of length q
            if (g > r) {
                ans += (g - r) * ((q + 1) / 2);
            }
            cout << ans << endl;
        } else {
            // Non-bipartite case (odd period M = xp + yp)
            // The graph decomposes into g components.
            // Each component corresponds to a problem on 0..L-1 with coprime steps xp, yp.
            // This reduces to MWIS on a cycle of clusters.
            ll q = n / g;
            ll r = n % g;
            ll ans = 0;
            
            if (r > 0) {
                ans += solve_instance(q + 1, xp, yp) * r;
            }
            if (g > r) {
                ans += solve_instance(q, xp, yp) * (g - r);
            }
            cout << ans << endl;
        }
    }
    return 0;
}