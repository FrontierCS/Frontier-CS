#include <iostream>
#include <vector>
#include <string>
#include <numeric>

// Function to perform a query for bakery c
char query(int c) {
    std::cout << "? " << c << std::endl;
    char response;
    std::cin >> response;
    return response;
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

    // Optimization for the case where memory is large enough for all bakeries
    if (k == n) {
        int distinct_count = 0;
        for (int i = 1; i <= n; ++i) {
            char res = query(i);
            if (res == 'N') {
                distinct_count++;
            }
        }
        answer(distinct_count);
        return 0;
    }
    
    std::vector<bool> is_unique(n + 1, true);
    int distinct_count = n;

    int block_size;
    if (k > 1) {
        block_size = k / 2;
    } else { // k=1, memory fits one item. A block can only be size 1.
        block_size = 1;
    }
    
    int num_blocks = n / block_size;

    std::vector<std::vector<int>> blocks(num_blocks);
    for (int i = 0; i < num_blocks; ++i) {
        for (int j = 0; j < block_size; ++j) {
            blocks[i].push_back(i * block_size + j + 1);
        }
    }

    // Iterate through m-1 passes, each corresponding to a perfect matching
    for (int s = 1; s < num_blocks; ++s) {
        reset();
        for (int i = 0; i < num_blocks; ++i) {
            // Process each pair in the matching defined by s once
            if (i < (i ^ s)) {
                int j = i ^ s;
                
                // Query first block of the pair
                for (int c : blocks[i]) {
                    if (is_unique[c]) {
                        // A 'Y' here means it's a duplicate of a type
                        // within this block queried earlier in this sequence.
                        if (query(c) == 'Y') {
                            is_unique[c] = false;
                            distinct_count--;
                        }
                    }
                }
                
                // Query second block of the pair
                for (int c : blocks[j]) {
                    if (is_unique[c]) {
                        // A 'Y' here means it's a duplicate of a type
                        // from the first block or from this block.
                        if (query(c) == 'Y') {
                            is_unique[c] = false;
                            distinct_count--;
                        }
                    }
                }
            }
        }
    }
    
    answer(distinct_count);

    return 0;
}