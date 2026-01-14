#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Wrapper for interaction
char query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    char res;
    cin >> res;
    return res;
}

struct Element {
    int id; // original index in the array a
    // We don't store value, we determine order.
};

int main() {
    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "! 1" << endl;
        return 0;
    }

    // We process from n down to 1
    // We maintain the list of indices sorted by their values
    // However, we only maintain the smallest 2 elements explicitly as the "pair"
    // and the rest are "sorted tail".
    // Actually, we just insert elements.
    // Based on the derivation:
    // We maintain the set of currently known smallest 2 elements from the processed suffix.
    // Let these be x and y.
    // We also maintain the rest of the sorted list `sorted_tail`.
    // The "pair" {x, y} are smaller than everything in `sorted_tail`.
    
    // State A: We know the relation between x and y (say x < y).
    // State B: We do not know the relation between x and y.
    
    // Initialization with last 2 elements
    // Indices n and n-1
    int x = n-1;
    int y = n;
    
    // Initial comparison to set to State A
    char c = query(x, y);
    if (c == '>') swap(x, y); // now x < y
    // State is A
    
    vector<int> sorted_tail; // stores indices > y in sorted order
    
    // Random generator for State B strategy
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    bool stateA = true; // true = A, false = B

    for (int i = n - 2; i >= 1; --i) {
        int z = i; // new element
        // In both states we will identify the max of {x, y, z}.
        // The max goes to sorted_tail. The other two become new {x, y}.
        
        if (stateA) {
            // State A: x < y known.
            // Compare y and z
            char res = query(y, z);
            if (res == '<') { 
                // y < z. Since x < y, max is z.
                // New pair {x, y} with x < y known.
                sorted_tail.push_back(z);
                stateA = true;
            } else {
                // z < y. Max is y.
                // New pair {x, z}. Relation x vs z unknown.
                sorted_tail.push_back(y);
                y = z; // new pair {x, z} (stored in x, y variables)
                // We don't know if x < z or z < x.
                stateA = false;
            }
        } else {
            // State B: x vs y unknown.
            // Randomly choose Strategy 1 or 2
            // S1: Compare x:y then winner:z
            // S2: Compare x:z (or y:z) then ...
            
            // Implementation of S1: Resolve x:y first
            // Implementation of S2: Resolve x:z first
            
            if (rng() % 2 == 0) {
                // Strategy 1: Compare x and y
                char r1 = query(x, y);
                if (r1 == '>') swap(x, y); // ensure x < y
                
                // Now compare y and z
                char r2 = query(y, z);
                if (r2 == '<') {
                    // y < z. Max z.
                    // Pair {x, y} with x < y.
                    sorted_tail.push_back(z);
                    stateA = true;
                } else {
                    // z < y. Max y.
                    // Pair {x, z} unknown.
                    sorted_tail.push_back(y);
                    y = z;
                    stateA = false;
                }
            } else {
                // Strategy 2: Compare x and z
                // (Symmetric to y and z, just pick one from pair)
                char r1 = query(x, z);
                if (r1 == '>') {
                    // x > z.
                    // Chain z < x. We still need max.
                    // Compare x and y
                    char r2 = query(x, y);
                    if (r2 == '<') {
                        // x < y. Max y.
                        // Pair {x, z} with z < x.
                        sorted_tail.push_back(y);
                        swap(x, z); // x becomes z (small), y becomes x (large) -> x < y
                        stateA = true;
                    } else {
                        // x > y. Max x.
                        // Pair {z, y} unknown.
                        sorted_tail.push_back(x);
                        x = z; // pair z, y
                        stateA = false;
                    }
                } else {
                    // x < z.
                    // Chain x < z.
                    // Compare z and y
                    char r2 = query(z, y);
                    if (r2 == '<') {
                        // z < y. Max y.
                        // Pair {x, z} with x < z.
                        sorted_tail.push_back(y);
                        y = z; // pair {x, z} -> x < y
                        stateA = true;
                    } else {
                        // z > y. Max z.
                        // Pair {x, y} unknown.
                        sorted_tail.push_back(z);
                        stateA = false;
                    }
                }
            }
        }
    }

    // Finally we have {x, y} and sorted_tail.
    // If stateB, we need to sort x, y.
    if (!stateA) {
        char c = query(x, y);
        if (c == '>') swap(x, y);
    }
    
    // Construct final result array
    // The smallest is x, then y, then sorted_tail reversed (wait, sorted_tail stores smallest to largest pushed?)
    // In our loop, we pushed the MAX of the triplet.
    // Since we process i from n-2 down to 1.
    // The values pushed earlier are larger?
    // Let's trace.
    // i=n-2. max of {n, n-1, n-2} is pushed. This is large.
    // i=1. max of { ... } is pushed. This is smaller.
    // Actually, sorted_tail contains elements in the order they were evicted.
    // The elements evicted later are smaller.
    // Because we are scanning from back (large indices) to front (small indices).
    // The "pair" keeps the smallest elements.
    // When we evict max, it is the largest of the current small triplet.
    // As we move i down, the triplet values generally decrease.
    // So sorted_tail is roughly decreasing.
    // We need to reverse sorted_tail to get increasing order?
    // No.
    // We have determined the full total order of indices.
    // The element `x` is the minimum (rank 1).
    // The element `y` is rank 2.
    // The last element pushed to sorted_tail was the max of {x, y, 1}. It is rank 3.
    // The first element pushed to sorted_tail was max of {n, n-1, n-2}. It is rank n.
    // So sorted_tail contains ranks [n, n-1, ..., 3].
    
    vector<int> p(n);
    p[x - 1] = 1;
    p[y - 1] = 2;
    
    int rank = 3;
    for (int i = sorted_tail.size() - 1; i >= 0; --i) {
        p[sorted_tail[i] - 1] = rank++;
    }
    
    cout << "!";
    for (int i = 0; i < n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;

    return 0;
}