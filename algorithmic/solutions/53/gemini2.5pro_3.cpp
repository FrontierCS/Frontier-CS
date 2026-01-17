#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

void solve() {
    int n;
    std::cin >> n;

    // We must choose a fixed k at the start. Let's pick k=n.
    // This means any query will not count edges originating from the k-th element of the query permutation.
    // By placing n at the k-th position, we effectively disable counting edges from n.
    // But our queries below will always have n at the last position, n, so k=n is a good choice.
    std::cout << n << std::endl;

    auto query = [&](const std::vector<int>& q) {
        std::cout << "?";
        for (int x : q) {
            std::cout << " " << x;
        }
        std::cout << std::endl;
        int res;
        std::cin >> res;
        if (res == -1) exit(0);
        return res;
    };

    // The core idea is to find p_i for i from 1 to n-1. p_n is then determined.
    // We can deduce properties of p_i and p_inv(i) using structured queries.
    //
    // Let S_A = sum_{a,b in A, a<b} [p_a = b].
    //
    // Base query: q = [1, 2, ..., n-1, n]. With k=n, the response is
    // C0 = S_{{1, ..., n-1}}. We run this once.
    std::vector<int> base_q(n);
    std::iota(base_q.begin(), base_q.end(), 1);
    int C0 = query(base_q);

    // For each i in {1, ..., n-1}, run a query with i at the start:
    // q_i = [i, (sorted {1..n-1} \ {i}), n].
    // Response A_i = [p_i is in {1..n-1}\{i}] + S_{{1..n-1}\{i}}.
    // Since p_i != i and p_i != n (we'll see why later), [p_i is in ...] is 1.
    // So, A_i = 1 + S_{{1..n-1}\{i}}.
    // S_{{1..n-1}\{i\}} = C0 - sum_{j<i} [p_j=i] - sum_{j>i} [p_i=j]
    // Since p is a permutation, sum_{j<i} [p_j=i] is either 0 or 1, and equals [p_inv(i) < i].
    // And sum_{j>i} [p_i=j] is also 0 or 1, and equals [p_i > i].
    // But our set is {1..n-1}, so it's [p_i > i and p_i < n].
    //
    // A simpler relation is for p_i < i.
    // A_i = 1 + C0 - [p_inv(i) < i] - [p_i < i].
    // Let B_i = C0 - (A_i - 1). Then B_i = [p_inv(i) < i] + [p_i < i].
    // This holds for i in {1, ..., n-1}.
    // This gives us crucial information about whether p_i and p_inv(i) are smaller than i.
    // B_i can be 0, 1, or 2.
    std::vector<int> B(n); // B[i] for i=1..n-1
    for (int i = 1; i < n; ++i) {
        std::vector<int> q(n);
        q[0] = i;
        int current = 1;
        for (int j = 1; j <= n; ++j) {
            if (j != i) {
                q[current++] = j;
            }
        }
        int Ai = query(q);
        B[i] = C0 - (Ai - 1);
    }
    
    std::vector<int> p(n + 1, 0);
    std::vector<bool> p_val_used(n + 1, false);

    // We can reconstruct p by iterating from n-1 down to 1.
    // At step i, we determine p_i or p_inv(i) by looking at B_i and which values/indices < i are available.
    for (int i = n - 1; i >= 1; --i) {
        if (p[i] != 0) continue; // already determined

        int unknown_preds_lt_i = 0;
        int last_unknown_pred = -1;
        for (int j = 1; j < i; ++j) {
            if (p[j] == 0) {
                unknown_preds_lt_i++;
                last_unknown_pred = j;
            }
        }

        // B[i] = [p_inv(i) < i] + [p_i < i].
        // [p_inv(i) < i] can be at most `unknown_preds_lt_i`.
        // If B[i] - unknown_preds_lt_i == 1, it must be that [p_inv(i) < i] is maxed out
        // AND [p_i < i] = 1. The only way for [p_inv(i)<i] to be `unknown_preds_lt_i` is if all unassigned j<i map to numbers >= i.
        // This logic is complex. A simpler deduction:
        // [p_i < i] = 1 means p_i must be one of the available values less than i.
        // If there's only one such value, we have found p_i.
        
        // This is a greedy approach based on the B values.
        int available_succs_lt_i = 0;
        int last_available_succ = -1;
        for (int j = 1; j < i; ++j) {
            if (!p_val_used[j]) {
                available_succs_lt_i++;
                last_available_succ = j;
            }
        }

        // if B[i] = [p_inv(i) < i] + [p_i < i]
        // [p_inv(i) < i] contributes at most `unknown_preds_lt_i`.
        // [p_i < i] contributes at most `available_succs_lt_i`.
        if (B[i] == unknown_preds_lt_i) { // This implies [p_i < i] = 0, so p_i > i
             // and [p_inv(i) < i] must be maximal.
             // We can find p_inv(i) as it must be last_unknown_pred
             if (unknown_preds_lt_i == 1) {
                 p[last_unknown_pred] = i;
                 p_val_used[i] = true;
             }
        } else { // B[i] must be unknown_preds_lt_i + 1, implies [p_i < i] = 1.
            // p_i must be last_available_succ
            if (available_succs_lt_i == 1) {
                p[i] = last_available_succ;
                p_val_used[last_available_succ] = true;
            }
        }
    }

    // After the loop, some values might still be zero.
    // This corresponds to the cycle involving n.
    // Specifically, if p_i = n, B_i logic might not determine it.
    // Let's find the element u such that p_u = n.
    int u = -1;
    for(int i = 1; i < n; ++i) {
        if(p[i] == 0) {
            u = i;
            break;
        }
    }
    if (u != -1) {
        p[u] = n;
        p_val_used[n] = true;
    }
    
    // p_n is the only value not used as an image yet.
    int v = -1;
    for(int i=1; i<=n; ++i) {
        if(!p_val_used[i]) {
            v = i;
            break;
        }
    }
    if(v != -1) {
        p[n] = v;
    }
    
    std::cout << "!";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}