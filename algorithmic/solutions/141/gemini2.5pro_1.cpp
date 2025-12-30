#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

bool query(int c) {
    std::cout << "? " << c << std::endl;
    char response;
    std::cin >> response;
    return response == 'Y';
}

void reset() {
    std::cout << "R" << std::endl;
}

void answer(int d) {
    std::cout << "! " << d << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, k;
    std::cin >> n >> k;

    std::vector<bool> is_first(n + 1, true);

    int num_blocks = n / k;

    // Phase 1: Intra-block duplicates
    for (int i = 0; i < num_blocks; ++i) {
        reset();
        int start = i * k + 1;
        int end = (i + 1) * k;
        for (int j = start; j <= end; ++j) {
            if (query(j)) {
                is_first[j] = false;
            }
        }
    }

    std::vector<std::vector<int>> block_cands(num_blocks);
    for (int i = 0; i < num_blocks; ++i) {
        int start = i * k + 1;
        int end = (i + 1) * k;
        for (int j = start; j <= end; ++j) {
            if (is_first[j]) {
                block_cands[i].push_back(j);
            }
        }
    }

    // Phase 2: Inter-block duplicates
    int chunk_size = k / 2;
    if (chunk_size == 0) { // Handles k=1 case
        chunk_size = 1;
    }
    
    for (int i = 0; i < num_blocks; ++i) {
        for (int j = i + 1; j < num_blocks; ++j) {
            for (size_t i_start = 0; i_start < block_cands[i].size(); i_start += chunk_size) {
                for (size_t j_start = 0; j_start < block_cands[j].size(); j_start += chunk_size) {
                    reset();
                    
                    size_t i_end = std::min(i_start + chunk_size, block_cands[i].size());
                    for (size_t l = i_start; l < i_end; ++l) {
                        query(block_cands[i][l]);
                    }

                    size_t j_end = std::min(j_start + chunk_size, block_cands[j].size());
                    for (size_t l = j_start; l < j_end; ++l) {
                        int bakery_idx = block_cands[j][l];
                        if (is_first[bakery_idx]) {
                            if (query(bakery_idx)) {
                                is_first[bakery_idx] = false;
                            }
                        }
                    }
                }
            }
        }
    }

    int distinct_count = 0;
    for (int i = 1; i <= n; ++i) {
        if (is_first[i]) {
            distinct_count++;
        }
    }

    answer(distinct_count);

    return 0;
}