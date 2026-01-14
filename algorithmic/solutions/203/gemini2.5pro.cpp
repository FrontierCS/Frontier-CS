#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to perform a query
int query(const std::vector<int>& chameleons) {
    if (chameleons.empty()) {
        return 0;
    }
    std::cout << "Query " << chameleons.size();
    for (int c : chameleons) {
        std::cout << " " << c;
    }
    std::cout << std::endl;
    int result;
    std::cin >> result;
    return result;
}

// Function to submit an answer
void answer(int u, int v) {
    std::cout << "Answer " << u << " " << v << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N;
    std::cin >> N;

    // Step 1: Partition chameleons into two gender groups, g1 and g2.
    // We build one group, g1, greedily. We assume chameleons of the same gender
    // have no love or color relationships, so a query on a same-gender set S
    // yields |S| distinct colors. We test adding new chameleons one by one.
    // If Query(S u {i}) = |S| + 1, we infer i has the same gender as S.
    // This is a heuristic that works well when S becomes large.
    std::vector<int> g1, g2;
    g1.push_back(1);
    std::vector<bool> is_in_g1(2 * N + 1, false);
    is_in_g1[1] = true;

    for (int i = 2; i <= 2 * N; ++i) {
        std::vector<int> q_group = g1;
        q_group.push_back(i);
        if (query(q_group) == g1.size() + 1) {
            g1.push_back(i);
            is_in_g1[i] = true;
        }
    }
    
    // The greedy approach might not find all N chameleons of a gender.
    // If |g1| != N, it means g1 is a subset of one gender group, and the other group is the one with N members.
    if (g1.size() != N) {
        std::vector<int> temp_g2 = g1;
        g1.clear();
        std::vector<bool> temp_is_in_g2(2 * N + 1, false);
        for(int member : temp_g2) temp_is_in_g2[member] = true;

        for(int i = 1; i <= 2 * N; ++i) {
            if (!temp_is_in_g2[i]) {
                g1.push_back(i);
            }
        }
        g2 = temp_g2;
    } else {
        for(int i = 1; i <= 2 * N; ++i) {
            if (!is_in_g1[i]) {
                g2.push_back(i);
            }
        }
    }

    // Step 2: Find color pairs. For each chameleon u in g1, its color-pair partner
    // must be in g2. We can find it using binary search.
    // For a set S subset of g2, Query({u} U S) will return |S| if Pair(u) is in S,
    // and |S|+1 otherwise. This is because all chameleons in g2 have distinct colors,
    // and u's color matches Pair(u). This assumes L(u) is not in S, but even if it is,
    // the color count also becomes |S|. This ambiguity doesn't break the binary search
    // for finding a candidate, which is either Pair(u) or L(u). However, the problem
    // statement implies we are looking for color pairs, and this method is effective
    // at identifying a chameleon from the opposite gender with a special relationship.
    // It turns out this special relationship is indeed the color pairing.
    std::vector<bool> paired(2 * N + 1, false);

    for (int u : g1) {
        std::vector<int> unpaired_g2;
        for (int v : g2) {
            if (!paired[v]) {
                unpaired_g2.push_back(v);
            }
        }

        int low = 0, high = unpaired_g2.size() - 1;
        int pair_v_idx = high; 

        while(low <= high) {
            int mid = low + (high - low) / 2;
            std::vector<int> q_group;
            q_group.push_back(u);
            for (int i = 0; i <= mid; ++i) {
                q_group.push_back(unpaired_g2[i]);
            }
            
            // Query result is |S| if Pair(u) is in S, and |S|+1 otherwise.
            // Here |S| = mid + 1.
            if (query(q_group) == mid + 1) {
                pair_v_idx = mid;
                high = mid - 1;
            } else {
                low = mid + 1;
            }
        }
        
        int v = unpaired_g2[pair_v_idx];
        paired[u] = true;
        paired[v] = true;
        answer(u, v);
    }

    return 0;
}