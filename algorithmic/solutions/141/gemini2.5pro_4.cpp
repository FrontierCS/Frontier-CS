#include <iostream>
#include <vector>
#include <string>
#include <numeric>

// Function to perform a query
bool query(int c) {
    std::cout << "? " << c << std::endl;
    char response;
    std::cin >> response;
    return response == 'Y';
}

// Function to perform a reset
void reset() {
    std::cout << "R" << std::endl;
}

// Function to output the final answer
void answer(int d) {
    std::cout << "! " << d << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, k;
    std::cin >> n >> k;

    std::vector<bool> is_new(n + 1, true);

    if (n == k) {
        reset();
        int distinct_count = 0;
        for (int i = 1; i <= n; ++i) {
            if (!query(i)) {
                distinct_count++;
            }
        }
        answer(distinct_count);
        return 0;
    }
    
    if (k == 1) {
        std::vector<int> representatives;
        for (int i = 1; i <= n; ++i) {
            bool is_duplicate = false;
            for (int rep : representatives) {
                reset();
                query(rep);
                if (query(i)) {
                    is_duplicate = true;
                    break;
                }
            }
            if (!is_duplicate) {
                representatives.push_back(i);
            }
        }
        answer(representatives.size());
        return 0;
    }

    int block_size = k / 2;
    int num_blocks = n / block_size;

    // Intra-block checks
    for (int i = 0; i < num_blocks; ++i) {
        reset();
        for (int j = 0; j < block_size; ++j) {
            int bakery_idx = i * block_size + j + 1;
            if (query(bakery_idx)) {
                is_new[bakery_idx] = false;
            }
        }
    }

    // Inter-block checks
    for (int i = 0; i < num_blocks; ++i) {
        for (int j = i + 1; j < num_blocks; ++j) {
            reset();
            for (int l = 0; l < block_size; ++l) {
                int bakery_idx_i = i * block_size + l + 1;
                query(bakery_idx_i);
            }
            for (int l = 0; l < block_size; ++l) {
                int bakery_idx_j = j * block_size + l + 1;
                if (is_new[bakery_idx_j]) {
                    if (query(bakery_idx_j)) {
                        is_new[bakery_idx_j] = false;
                    }
                }
            }
        }
    }

    int distinct_count = 0;
    for (int i = 1; i <= n; ++i) {
        if (is_new[i]) {
            distinct_count++;
        }
    }
    answer(distinct_count);

    return 0;
}