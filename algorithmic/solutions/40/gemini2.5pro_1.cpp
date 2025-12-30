#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

// Function to perform a query and read the result.
int perform_query(const std::vector<int>& indices) {
    if (indices.empty()) {
        return 0;
    }
    std::cout << "0 " << indices.size();
    for (int idx : indices) {
        std::cout << " " << idx;
    }
    std::cout << std::endl;
    int result;
    std::cin >> result;
    if (result == -1) {
        exit(0);
    }
    return result;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    // Find the first opening bracket.
    // Assume s_1 is '('. Its match must be somewhere.
    // We can binary search for the first '('.
    // check(k) will tell if s_k is '('.
    // A char s_k is '(' if there exists some ')' at j > k.
    // So query {k, k+1, ..., n}. If f > 0, it suggests a pair exists.
    // But f>0 could be due to pairs within {k+1, ..., n}.
    // A better check: is f({k, ..., n}) > f({k+1, ..., n})?
    // This implies s_k participated in a new RBS, so it must be '('.

    std::vector<int> all_indices_from_k(n);
    std::iota(all_indices_from_k.begin(), all_indices_from_k.end(), 1);
    
    int f_all = perform_query(all_indices_from_k);

    int first_open_idx = -1;
    int low = 1, high = n;

    while(low <= high) {
        int mid = low + (high - low) / 2;
        if (mid == n) {
             // If we reach here, s_n must be '('.
             // This check helps avoid querying with an empty set for mid+1..n
             // The logic below will handle it.
             high = mid -1;
             continue;
        }
        
        std::vector<int> indices_from_mid;
        for(int i = mid; i <= n; ++i) indices_from_mid.push_back(i);
        int f_from_mid = perform_query(indices_from_mid);
        
        std::vector<int> indices_from_mid_plus_1;
        for(int i = mid + 1; i <= n; ++i) indices_from_mid_plus_1.push_back(i);
        int f_from_mid_plus_1 = perform_query(indices_from_mid_plus_1);

        if (f_from_mid > f_from_mid_plus_1) {
            first_open_idx = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    
    // If binary search didn't find one, it implies the logic is flawed for some structures.
    // The problem guarantees at least one '(' and one ')'.
    // The first ')' can't form a new RBS with a later part of the string.
    // The first '(' can. So f(s_k..n) > f(s_{k+1}..n) implies s_k='('.
    // If this holds for multiple k, we find the first such k.
    // The last possible first '(' is at n-1. If we haven't found one by then, s_n must be ')'.
    // If the loop finishes without finding one, `first_open_idx` will be -1.
    // This case might happen if all '(' are at the end.
    // For s = "))((", f(1..4)=1, f(2..4)=1, f(3..4)=1, f(4..4)=0. So k=3 is found.
    if(first_open_idx == -1) first_open_idx = n;


    std::string s(n, ' ');
    s[first_open_idx - 1] = '(';

    for (int i = 1; i <= n; ++i) {
        if (i == first_open_idx) continue;
        if (perform_query({first_open_idx, i}) == 1) {
            s[i - 1] = ')';
        } else {
            s[i - 1] = '(';
        }
    }

    std::cout << "1 " << s << std::endl;

    return 0;
}