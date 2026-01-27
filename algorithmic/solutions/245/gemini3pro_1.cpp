#include <iostream>
#include <vector>
#include <cstdlib>
#include <algorithm>

using namespace std;

// Function to query the interactor.
// Returns 1 if player i thinks player j is a Knight, 0 otherwise.
int query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) {
        exit(0); // Terminate immediately on invalid query/error
    }
    return res;
}

void solve() {
    int n;
    if (!(cin >> n)) return;

    int u = -1, v = -1;
    int x_u = -1, x_v = -1;

    // We pair up players (1,2), (3,4), etc. and query them against each other.
    // Based on the game rules:
    // - Pairs consisting of (Knight, Knight) yield answers (1, 1).
    // - Pairs consisting of (Knave, Knave) yield answers (1, 1).
    // - Pairs consisting of (Knight, Knave) yield answers (0, 0).
    // These are "symmetric" responses.
    //
    // The Impostor is the only one who breaks this symmetry when paired.
    // - (Knight, Impostor): Knight says 1 (thinks I is K), Impostor says 0 (lies about K). -> (1, 0)
    // - (Knave, Impostor): Knave says 0 (lies about I being K), Impostor says 1 (lies about L). -> (0, 1)
    //
    // Since there is exactly one Impostor, we scan pairs until we find an asymmetric result.
    // If n is odd and no pair is found, the last player is the Impostor.
    
    for (int i = 1; i < n; i += 2) {
        int r1 = query(i, i + 1);
        int r2 = query(i + 1, i);
        
        if (r1 != r2) {
            u = i;
            v = i + 1;
            x_u = r1;
            x_v = r2;
            break; // Found the Impostor candidate pair
        }
    }

    if (u == -1) {
        // No asymmetric pair found, Impostor is the last player (n is odd)
        cout << "! " << n << endl;
        return;
    }

    // We have an asymmetric pair {u, v}.
    // Normalize such that u is the one who answered 1 and v answered 0.
    if (x_u == 0) {
        swap(u, v);
        swap(x_u, x_v);
    }
    // Now: query(u, v) == 1 and query(v, u) == 0.
    // This leaves two scenarios for (u, v):
    // Case 1: (Knight, Impostor). u=K, v=I.
    // Case 2: (Impostor, Knave). u=I, v=L.
    
    // To distinguish, we use a third player w (witness) distinct from u and v.
    int w = 1;
    while (w == u || w == v) w++;

    // We compare query(w, v) and query(v, w).
    // In Case 1 (v is Impostor):
    //    w -> v (target I) behaves like w -> K.
    //    v -> w (speaker I) behaves like L -> w.
    //    If w is Knight: w->I is 1. I->w (L->K) is 0. (Different)
    //    If w is Knave:  w->I is 0. I->w (L->L) is 1. (Different)
    // In Case 2 (u is Impostor, v is Knave):
    //    w -> v (target L) behaves like w -> L.
    //    v -> w (speaker L) behaves like L -> w.
    //    If w is Knight: w->L is 0. L->w (L->K) is 0. (Same)
    //    If w is Knave:  w->L is 1. L->w (L->L) is 1. (Same)
    
    int A = query(w, v);
    int B = query(v, w);

    if (A == B) {
        // Case 2: u is the Impostor
        cout << "! " << u << endl;
    } else {
        // Case 1: v is the Impostor
        cout << "! " << v << endl;
    }
}

int main() {
    // Fast I/O is good practice, though less critical for interactive problems
    // due to frequent flushing.
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}