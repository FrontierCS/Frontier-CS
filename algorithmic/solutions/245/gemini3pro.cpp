#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Function to perform a query to the interactive judge
// Returns 1 if player i thinks player j is a Knight, 0 otherwise.
int query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int ans;
    cin >> ans;
    if (ans == -1) exit(0); // Invalid query or error
    return ans;
}

void solve() {
    int n;
    if (!(cin >> n)) return;
    
    // Players are numbered 1 to n
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);
    
    // Random shuffle the processing order.
    // This helps in achieving an average case of N/2 queries to find the relevant pair,
    // which is beneficial for the total cost score.
    random_device rd;
    mt19937 g(rd());
    shuffle(p.begin(), p.end(), g);

    int impostor = -1;
    
    // We iterate through players in pairs (u, v).
    // For each pair, we ask ? u v and ? v u.
    // Based on the game rules:
    // - Knight/Knight: 1, 1 (Symmetric)
    // - Knave/Knave: 1, 1 (Symmetric)
    // - Knight/Knave: 0, 0 (Symmetric)
    // - Knight/Impostor: 1, 0 (Asymmetric)
    // - Knave/Impostor: 0, 1 (Asymmetric)
    // Thus, a pair is asymmetric if and only if exactly one of them is the Impostor.
    
    for (int k = 0; k + 1 < n; k += 2) {
        int u = p[k];
        int v = p[k + 1];
        
        int ans1 = query(u, v);
        int ans2 = query(v, u);
        
        if (ans1 != ans2) {
            // Found an asymmetric pair. The Impostor is either u or v.
            // To distinguish, we use a third player 'w' as a witness.
            // 'w' must be a player who is NOT the Impostor.
            // Since the Impostor is in {u, v}, any player outside this set is safe.
            
            int w;
            if (k > 0) {
                // If this is not the first pair, we can pick a player from the first pair (p[0]),
                // which was already checked and found symmetric (so p[0] is not Impostor).
                w = p[0];
            } else {
                // If this is the first pair, pick the last player p[n-1].
                // Since n >= 3, p[n-1] is distinct from u (p[0]) and v (p[1]).
                // p[n-1] cannot be the Impostor because the Impostor is in {u, v}.
                w = p[n - 1];
            }
            
            // Check u against the safe witness w.
            // If u were Knight/Knave (not Impostor), interaction with safe w would be symmetric.
            // If u is Impostor, interaction with safe w would be asymmetric.
            int q1 = query(u, w);
            int q2 = query(w, u);
            
            if (q1 != q2) {
                impostor = u;
            } else {
                impostor = v;
            }
            
            // Impostor identified.
            break;
        }
    }
    
    if (impostor == -1) {
        // If n is odd and we went through all pairs without finding asymmetry,
        // the Impostor must be the leftover player.
        // (It's guaranteed one Impostor exists).
        impostor = p[n - 1];
    }
    
    cout << "! " << impostor << endl;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}