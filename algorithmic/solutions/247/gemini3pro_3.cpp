#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

using namespace std;

struct Op {
    int i, j;
};

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N;
    if (!(cin >> N)) return 0;
    
    vector<int> A(N + 1);
    for (int i = 1; i <= N; ++i) cin >> A[i];
    
    vector<int> B(N + 1);
    for (int i = 1; i <= N; ++i) cin >> B[i];
    
    // Check total sum equality
    long long sumA = 0, sumB = 0;
    for(int i=1; i<=N; ++i) sumA += A[i];
    for(int i=1; i<=N; ++i) sumB += B[i];
    if(sumA != sumB) {
        cout << "No" << endl;
        return 0;
    }
    
    // Check prefix sum condition for C_i = A_i - i vs D_i = B_i - i
    // Condition: sum_{1..k} C_i <= sum_{1..k} D_i for all k
    vector<long long> C(N + 1), D(N + 1);
    for(int i=1; i<=N; ++i) C[i] = A[i] - i;
    for(int i=1; i<=N; ++i) D[i] = B[i] - i;
    
    long long prefC = 0, prefD = 0;
    for(int i=1; i<=N; ++i) {
        prefC += C[i];
        prefD += D[i];
        if(prefC > prefD) {
            cout << "No" << endl;
            return 0;
        }
    }
    
    vector<Op> ops;
    
    for (int i = 1; i <= N; ++i) {
        if (A[i] == B[i]) continue;
        
        // We need to transform A[i] to B[i].
        // Since we process left to right and satisfy i, we must bring a value from some k > i.
        // Moving a value from k to i (leftwards) decreases its value by the number of swaps.
        // Let num_ops be the number of swaps used.
        // Final value at i = A[k] - num_ops.
        // We need A[k] - num_ops == B[i] => num_ops = A[k] - B[i].
        // The distance is dist = k - i.
        // Each swap moves the element by at least 1 position. So we need num_ops <= dist.
        // Also num_ops >= 1 since k > i.
        
        int best_k = -1;
        int min_ops = 2e9; // Large enough value
        
        for (int k = i + 1; k <= N; ++k) {
            int needed_ops = A[k] - B[i];
            // Check if valid
            if (needed_ops >= 1 && needed_ops <= k - i) {
                // We want to minimize operations.
                // Secondary criteria: smaller k is better (arbitrary/heuristic)
                if (needed_ops < min_ops) {
                    min_ops = needed_ops;
                    best_k = k;
                }
            }
        }
        
        if (best_k == -1) {
            cout << "No" << endl;
            return 0;
        }
        
        // Execute the moves
        // We need to cover distance `dist` with `jumps` steps.
        // To minimize disruption to other elements (reducing their C value makes condition tighter),
        // we should try to keep other elements' C values high.
        // Large jump for our element implies the other element moves large distance right, 
        // reducing its C value.
        // Small jump implies other element moves 1 right, C value constant.
        // However, we MUST perform exactly `min_ops` swaps.
        // If min_ops < dist, we are forced to do some jumps > 1.
        // We perform one large jump of size `dist - (min_ops - 1)` first,
        // then `min_ops - 1` jumps of size 1.
        
        int current_pos = best_k;
        int jumps = min_ops;
        int dist = current_pos - i;
        
        int first_jump_size = dist - (jumps - 1);
        
        // 1. Large jump
        int next_pos = current_pos - first_jump_size;
        ops.push_back({next_pos, current_pos});
        
        // Apply swap effect
        int u = next_pos;
        int v = current_pos;
        int val_u = A[u];
        int val_v = A[v];
        A[u] = val_v - 1;
        A[v] = val_u + 1;
        
        current_pos = next_pos;
        
        // 2. Small jumps
        for (int step = 0; step < jumps - 1; ++step) {
            next_pos = current_pos - 1;
            ops.push_back({next_pos, current_pos});
            
            u = next_pos;
            v = current_pos;
            val_u = A[u];
            val_v = A[v];
            A[u] = val_v - 1;
            A[v] = val_u + 1;
            
            current_pos = next_pos;
        }
        
        // Verify (Debugging / Sanity Check)
        if (A[i] != B[i]) {
            cout << "No" << endl;
            return 0;
        }
    }
    
    cout << "Yes" << endl;
    cout << ops.size() << endl;
    for (const auto& op : ops) {
        cout << op.i << " " << op.j << "\n";
    }
    
    return 0;
}