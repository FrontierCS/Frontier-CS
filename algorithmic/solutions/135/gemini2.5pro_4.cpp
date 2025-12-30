#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <random>
#include <set>
#include <map>
#include <chrono>
#include <tuple>

using namespace std;

int K, N;
map<tuple<int, int, int>, set<pair<int, int>>> query_cache;

// Function to ask a query and parse the response
set<pair<int, int>> ask(int x, int y, int z) {
    if (x > y) swap(x, y);
    if (y > z) swap(y, z);
    if (x > y) swap(x, y);
    
    if (query_cache.count({x, y, z})) {
        return query_cache[{x, y, z}];
    }

    cout << "? " << x << " " << y << " " << z << endl;
    int r;
    cin >> r;
    set<pair<int, int>> result;
    for (int i = 0; i < r; ++i) {
        int u, v;
        cin >> u >> v;
        if (u > v) swap(u, v);
        result.insert({u, v});
    }
    query_cache[{x,y,z}] = result;
    return result;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> K >> N;

    // Step 1: Find an adjacent pair {p1, p2}
    // Fix p1 = 0 and find its neighbor p2 by random sampling.
    // A door j is a neighbor of p1 if it has a small distance d(p1, j).
    // In a query "? p1 b c", if d(p1, b) is small, {p1, b} is likely to be a closest pair.
    // So we give scores to doors based on how often they form a closest pair with p1.
    // The door with the highest score is very likely a neighbor.
    int p1 = 0;
    int p2 = -1;

    vector<int> candidates;
    for (int i = 1; i < N; ++i) {
        candidates.push_back(i);
    }
    
    if (N <= 30) { // For small N, a deterministic method is better.
        p2 = 1;
        for (int i = 2; i < N; ++i) {
            auto res = ask(p1, p2, i);
            if(res.count({min(p1, i), max(p1, i)})) {
                // This implies d(p1, i) <= d(p1, p2).
                // It's a simple tournament to find the closest node to p1.
                p2 = i;
            }
        }
    } else {
        vector<int> scores(N, 0);
        mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
        
        int num_queries = 4000;
        if (K < 5000) num_queries = K - (N * (log2(N)+1) + 2*N);
        num_queries = max(100, num_queries);

        for (int i = 0; i < num_queries && candidates.size() >= 2; ++i) {
            shuffle(candidates.begin(), candidates.end(), rng);
            int b = candidates[0];
            int c = candidates[1];
            auto res = ask(p1, b, c);
            if (res.count({min(p1, b), max(p1, b)})) {
                scores[b]++;
            }
            if (res.count({min(p1, c), max(p1, c)})) {
                scores[c]++;
            }
        }

        int max_score = -1;
        for (int i = 1; i < N; ++i) {
            if (scores[i] > max_score) {
                max_score = scores[i];
                p2 = i;
            }
        }
    }

    // Step 2: Find p1's other neighbor, p3.
    // We sort all other doors by distance from p1. The closest one is p3.
    // A comparator for d(p,x) < d(p,y) for x,y on the same semi-circle from p:
    // query(? p x y), if {p,y} is NOT a closest pair, then x is closer.
    vector<int> U;
    for(int i=0; i<N; ++i) if (i!=p1 && i!=p2) U.push_back(i);

    sort(U.begin(), U.end(), [&](int x, int y) {
        auto res = ask(p1, x, y);
        // This comparator is a bit of a heuristic for general points, but works well for sorting by distance.
        bool has_x = res.count({min(p1,x), max(p1,x)});
        bool has_y = res.count({min(p1,y), max(p1,y)});
        if(has_x != has_y) return has_y;
        return x < y; // for stability
    });

    int p3 = U[0];
    
    // Step 3: Partition remaining doors into two semi-circles.
    // We have a chain p3-p1-p2. The diameter perpendicular to the chord p3-p2 splits the circle.
    // Querying "? p2 p3 x" tells us if x is closer to p2 or p3.
    vector<int> h1, h2; // h1 closer to p2, h2 closer to p3
    for(size_t i=1; i<U.size(); ++i) {
        int x = U[i];
        auto res = ask(p2, p3, x);
        if(res.count({min(p2,x), max(p2,x)})) {
            h1.push_back(x);
        } else {
            h2.push_back(x);
        }
    }
    
    // Step 4: Sort each semi-circle.
    sort(h1.begin(), h1.end(), [&](int x, int y) {
        auto res = ask(p2, x, y);
        return !res.count({min(p2, y), max(p2, y)});
    });

    sort(h2.begin(), h2.end(), [&](int x, int y) {
        auto res = ask(p3, x, y);
        return !res.count({min(p3, y), max(p3, y)});
    });

    // Step 5: Assemble the final order.
    // The order is ...h2_rev, p3, p1, p2, h1...
    vector<int> final_order;
    reverse(h2.begin(), h2.end());

    for (int x : h2) final_order.push_back(x);
    final_order.push_back(p3);
    final_order.push_back(p1);
    final_order.push_back(p2);
    for (int x : h1) final_order.push_back(x);
    
    // The orientation of one semi-circle might be flipped.
    // We check if p2 is neighbor of p1. If not, the whole sequence must be reversed.
    int p1_idx = -1;
    for(int i=0; i<N; ++i) if(final_order[i] == p1) p1_idx = i;
    
    int next_p1 = final_order[(p1_idx + 1)%N];
    if(next_p1 != p2) {
       reverse(final_order.begin(), final_order.end());
    }

    cout << "! ";
    for (int i = 0; i < N; ++i) {
        cout << final_order[i] << (i == N - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}