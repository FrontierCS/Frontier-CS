#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cassert>

// Wrapper for queries to adhere to 1-based indexing for the problem
char query(int i, int j) {
    std::cout << "? " << i + 1 << " " << j + 1 << std::endl;
    char response;
    std::cin >> response;
    if (response == '0') exit(0); // Exit on error
    return response;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> p(n);

    // Handle small cases separately
    if (n <= 2) {
        if (n == 1) {
            p[0] = 1;
        } else {
            char res = query(0, 1);
            if (res == '<') {
                p[0] = 1;
                p[1] = 2;
            } else {
                p[0] = 2;
                p[1] = 1;
            }
        }
    } else {
        std::vector<int> medians_indices;
        std::vector<std::vector<int>> blocks;
        
        // Process in blocks of 3
        for (int i = 0; i < n / 3; ++i) {
            int i1 = 3 * i;
            int i2 = 3 * i + 1;
            int i3 = 3 * i + 2;

            // Find the median of three elements.
            // This can be done in 2-3 queries.
            // A simple method: compare p[i1] to p[i2] and p[i3].
            // If results differ, p[i1] is the median.
            // Otherwise, p[i1] is min or max, and one more query finds median of p[i2], p[i3].
            char res12 = query(i1, i2);
            char res13 = query(i1, i3);

            int median_idx;
            int other1, other2;

            if (res12 == res13) { // p[i1] is either smallest or largest
                median_idx = (query(i2, i3) == '<') ? i3 : i2;
            } else { // p[i1] is the median
                median_idx = i1;
            }
            
            medians_indices.push_back(median_idx);
            
            std::vector<int> current_block = {i1, i2, i3};
            blocks.push_back(current_block);
        }
        
        // Sort the median indices based on their values
        std::sort(medians_indices.begin(), medians_indices.end(), [&](int i, int j) {
            return query(i, j) == '<';
        });

        // Assign values based on sorted medians
        for (size_t i = 0; i < medians_indices.size(); ++i) {
            int median_idx = medians_indices[i];
            p[median_idx] = 3 * i + 2;
            
            // Find which block this median belongs to
            int block_idx = -1;
            for(size_t j=0; j<blocks.size(); ++j) {
                bool found = false;
                for(int k=0; k<3; ++k) {
                    if (blocks[j][k] == median_idx) {
                        found = true;
                        break;
                    }
                }
                if (found) {
                    block_idx = j;
                    break;
                }
            }

            int other1 = -1, other2 = -1;
            for (int val : blocks[block_idx]) {
                if (val != median_idx) {
                    if (other1 == -1) other1 = val;
                    else other2 = val;
                }
            }
            
            // Assign values to the other two elements in the block
            if (query(other1, other2) == '<') {
                p[other1] = 3 * i + 1;
                p[other2] = 3 * i + 3;
            } else {
                p[other2] = 3 * i + 1;
                p[other1] = 3 * i + 3;
            }
        }

        // Handle the remainder if n is not a multiple of 3
        if (n % 3 == 1) {
            p[n - 1] = n;
        } else if (n % 3 == 2) {
            int i1 = n - 2;
            int i2 = n - 1;
            if (query(i1, i2) == '<') {
                p[i1] = n - 1;
                p[i2] = n;
            } else {
                p[i2] = n - 1;
                p[i1] = n;
            }
        }
    }
    
    // Output the final array
    std::cout << "! ";
    for (int i = 0; i < n; ++i) {
        std::cout << p[i] << (i == n - 1 ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}