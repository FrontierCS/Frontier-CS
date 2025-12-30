#include <iostream>
#include <vector>
#include <utility>

// Function to perform a query
std::pair<int, int> do_query(int i) {
    std::cout << "? " << i << std::endl;
    int a0, a1;
    std::cin >> a0 >> a1;
    return {a0, a1};
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    int p = 0;
    auto res = do_query(p);
    int k = res.first + res.second;

    while (k > 0) {
        int best_p = -1;
        int best_k = k;
        
        int l = 0, r = n - 1;
        // Binary search for the smallest index with a more valuable prize
        while (l <= r) {
            int mid = l + (r - l) / 2;
            auto mid_res = do_query(mid);
            int mid_k = mid_res.first + mid_res.second;

            if (mid_k < k) {
                best_p = mid;
                best_k = mid_k;
                r = mid - 1;
            } else {
                l = mid + 1;
            }
        }
        
        p = best_p;
        k = best_k;
    }

    std::cout << "! " << p << std::endl;

    return 0;
}