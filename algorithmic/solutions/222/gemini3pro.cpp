#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Function to query the interactor
// v: start vertex
// x: number of steps
// Returns the vertex index after x steps
int query(int v, long long x) {
    cout << "? " << v << " " << x << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Exit immediately on invalid query/error
    return res;
}

// Function to report the answer
void report(long long s) {
    cout << "! " << s << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Exit immediately on Wrong Answer
}

void solve() {
    // Start from vertex 1. Move 1 step to ensure we are on the cycle.
    // The problem states that for every edge u->v, v is on the cycle.
    // So 1 step from any vertex lands us on the cycle.
    int S = query(1, 1);

    // We use a Baby-step Giant-step algorithm to find the cycle length L.
    // L <= 10^6.
    // We choose block size B = 1000, which is sqrt(10^6).
    // This balances phase 1 and phase 2 queries to be around 1000 each.
    // Total queries approx 2000, which is within the 2500 limit.
    const int B = 1000;
    
    // visited array to store distance from S for vertices encountered in Phase 1.
    // Vertices are 1-indexed up to 10^6.
    vector<int> visited(1000001, -1);

    visited[S] = 0;
    int curr = S;
    long long multiple = -1;

    // Phase 1: Baby steps
    // Move 1 step at a time up to B times.
    for (int i = 1; i <= B; ++i) {
        curr = query(curr, 1);
        if (visited[curr] != -1) {
            // Collision found
            multiple = i - visited[curr];
            break;
        }
        visited[curr] = i;
    }

    // Phase 2: Giant steps
    // If collision not found in Phase 1, move by B steps at a time.
    // We start from the current position which is at distance B from S.
    if (multiple == -1) {
        long long current_dist = B;
        // We need to cover up to 10^6. With step B=1000, we need 1000 more steps.
        // We use slightly more to be safe (up to limit).
        // Total allowed queries 2500. Used ~1000. Left ~1500.
        for (int k = 0; k < 1400; ++k) {
            curr = query(curr, B);
            current_dist += B;
            if (visited[curr] != -1) {
                // Collision with a vertex from Phase 1
                // The current vertex is at 'current_dist' from S.
                // It matches a vertex at 'visited[curr]' from S.
                // So L divides (current_dist - visited[curr]).
                multiple = current_dist - visited[curr];
                break;
            }
            // Optimization: we could add these vertices to visited to speed up detection
            // if we hit a giant step node again.
            // However, ensuring we match Phase 1 guarantees we find a multiple close to L.
            visited[curr] = (int)(current_dist % 2000000000); 
        }
    }
    
    // multiple is a multiple of the cycle length L.
    // We now need to find the smallest divisor d of multiple such that moving d steps from S returns S.
    long long ans = multiple;
    long long temp = multiple;
    
    // Factorize temp to check divisors
    for (long long i = 2; i * i <= temp; ++i) {
        if (temp % i == 0) {
            bool possible = true;
            while (temp % i == 0) {
                if (possible) {
                    long long cand = ans / i;
                    if (query(S, cand) == S) {
                        ans = cand;
                    } else {
                        possible = false; // Cannot reduce by this factor anymore
                    }
                }
                temp /= i;
            }
        }
    }
    if (temp > 1) {
        long long cand = ans / temp;
        if (query(S, cand) == S) {
            ans = cand;
        }
    }
    
    report(ans);
}

int main() {
    // Optimization for I/O not strictly necessary for interaction but good practice
    // Removing sync allows mixed C/C++ I/O but here we only use C++ streams.
    // Do not untie cin from cout for interactive problems usually, but flushing handles it.
    
    int n;
    if (cin >> n) {
        while (n--) {
            solve();
        }
    }
    return 0;
}