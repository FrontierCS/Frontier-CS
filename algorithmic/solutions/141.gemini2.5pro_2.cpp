#include <iostream>
#include <vector>
#include <string>

// Helper function to perform a query and read the response.
char query(int c) {
    std::cout << "? " << c << std::endl;
    char response;
    std::cin >> response;
    return response;
}

// Helper function to perform a reset.
void reset() {
    std::cout << "R" << std::endl;
}

// Helper function to output the final answer.
void answer(int d) {
    std::cout << "! " << d << std::endl;
}

int main() {
    // Use fast I/O.
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, k;
    std::cin >> n >> k;

    // is_first[i] is true if we haven't found a j < i with a_j = a_i.
    // We start by assuming all bakeries are unique.
    std::vector<bool> is_first(n + 1, true);

    int block_size = k;
    int num_blocks = n / block_size;

    // Iterate over all pairs of blocks (i, j) where i <= j.
    for (int i = 0; i < num_blocks; ++i) {
        for (int j = i; j < num_blocks; ++j) {
            reset();
            
            if (i == j) {
                // Handle intra-block duplicates.
                // For each potentially unique bakery, query it. A 'Y' means it's a
                // duplicate of a bakery previously queried within this same block.
                for (int u_idx = i * block_size + 1; u_idx <= (i + 1) * block_size; ++u_idx) {
                    if (is_first[u_idx]) {
                        if (query(u_idx) == 'Y') {
                            is_first[u_idx] = false;
                        }
                    }
                }
            } else {
                // Handle inter-block duplicates.
                // First, load potentially unique items from block i into memory.
                for (int u_idx = i * block_size + 1; u_idx <= (i + 1) * block_size; ++u_idx) {
                    if (is_first[u_idx]) {
                        query(u_idx);
                    }
                }
                // Then, check items from block j against memory.
                // A 'Y' means it's a duplicate of something in block i or an earlier
                // element in block j.
                for (int v_idx = j * block_size + 1; v_idx <= (j + 1) * block_size; ++v_idx) {
                    if (is_first[v_idx]) {
                        if (query(v_idx) == 'Y') {
                            is_first[v_idx] = false;
                        }
                    }
                }
            }
        }
    }

    // Count the number of bakeries that are the first of their cake type.
    int distinct_count = 0;
    for (int i = 1; i <= n; ++i) {
        if (is_first[i]) {
            distinct_count++;
        }
    }

    answer(distinct_count);

    return 0;
}