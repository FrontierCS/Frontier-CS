#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <map>
#include <algorithm>
#include <random>

using namespace std;

long long ask(long long u, long long d) {
    cout << "? " << u << " " << d << endl;
    long long response;
    cin >> response;
    return response;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int h;
    cin >> h;

    long long n = (1LL << h) - 1;

    vector<long long> p(n);
    iota(p.begin(), p.end(), 1);
    
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    shuffle(p.begin(), p.end(), rng);

    long long u_root = -1;
    int root_queries = 0;
    
    // The only node v for which max_dist(v) = h-1 is the root.
    // So for any other node v', max_dist(v') > h-1.
    // Querying at dist h will be 0 only for the root, assuming there are nodes with positive weights.
    // If weights can all be zero, this problem is trivial (sum is 0).
    // So this is a reliable way to find the root.
    for (long long u : p) {
        // Heuristic limit for typical cases to save queries, then do exhaustive search if needed.
        if (h > 8 && root_queries >= 400) { 
             break;
        }
        if (ask(u, h) == 0) {
            u_root = u;
            break;
        }
        root_queries++;
    }

    if (u_root == -1) {
       for(long long u = 1; u <= n; ++u) {
          // Check if u was already checked in the random sample
          bool checked = false;
          for(int i=0; i<root_queries; ++i) if(p[i] == u) checked = true;
          if(checked) continue;

          if (ask(u, h) == 0) {
            u_root = u;
            break;
          }
       }
    }

    long long sum_minus_f1 = 0;
    for (int d = 1; d < h; ++d) {
        sum_minus_f1 += ask(u_root, d);
    }

    // Now find f1. A query (? u, h-1) gives f1 if p_u is a leaf.
    // There are (n+1)/2 leaves, which is >50% of nodes.
    // The most frequent response to (? u, h-1) should be f1.
    map<long long, int> counts;
    int f1_queries = 0;
    shuffle(p.begin(), p.end(), rng);

    for (long long u : p) {
        if (u == u_root) continue;
        
        if (h > 8 && f1_queries >= 400) break;
        
        long long res = ask(u, h - 1);
        if (res > 0) {
           counts[res]++;
        }
        f1_queries++;
    }
    
    long long f1 = -1;
    if (!counts.empty()) {
        long long max_count = 0;
        for(auto const& [val, num] : counts){
            if(num > max_count){
                max_count = num;
                f1 = val;
            }
        }
    } else {
        // Fallback: If heuristic fails (e.g. all sampled nodes were non-leaves
        // or weights made responses 0), find a guaranteed leaf.
        // A node is a leaf iff max_dist is 2h-2.
        // So ask(u, 2h-2) can be > 0 only if p_u is a leaf.
        long long u_leaf = -1;
        shuffle(p.begin(), p.end(), rng);
        for (long long u : p) {
            if (u == u_root) continue;
            if (ask(u, 2 * h - 2) > 0) {
                u_leaf = u;
                break;
            }
        }
        if (u_leaf != -1) {
            f1 = ask(u_leaf, h - 1);
        } else {
             // Absolute worst case: can't find a leaf with non-zero weight path.
             // This case is extremely unlikely. The sum would likely be 0.
             f1 = 0;
        }
    }

    cout << "! " << sum_minus_f1 + f1 << endl;

    return 0;
}