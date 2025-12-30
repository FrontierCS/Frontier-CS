#include <iostream>
#include <vector>
#include <string>
#include <numeric>

const long long M = 1000000007;

void issue_query(int n, const std::vector<long long>& a) {
    std::cout << "?";
    for (int i = 0; i <= n; ++i) {
        std::cout << " " << a[i];
    }
    std::cout << std::endl;
}

long long read_response() {
    long long r;
    std::cin >> r;
    return r;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> ops(n + 1, 0);
    long long total_plus_count = -1;
    long long V = n + 2;

    // First query to find op_1 and total_plus_count
    std::vector<long long> a(n + 1, 1);
    a[0] = 2;
    a[1] = V;
    issue_query(n, a);
    long long r1 = read_response();

    long long cand1 = (r1 - (V + 1) % M + M) % M;
    long long cand2 = (r1 - (2 * V) % M + M) % M;

    if (cand1 >= 0 && cand1 <= n) {
        ops[1] = 0; // +
        total_plus_count = cand1;
    } else {
        ops[1] = 1; // *
        total_plus_count = cand2;
    }

    long long plus_count_prefix = (ops[1] == 0);

    for (int k = 2; k <= n; ++k) {
        std::fill(a.begin(), a.end(), 1);
        a[0] = 2;
        a[k] = V;

        issue_query(n, a);
        long long rk = read_response();

        long long expected_if_plus = (V + total_plus_count + 1) % M;

        if (rk == expected_if_plus) {
            ops[k] = 0; // +
        } else {
            ops[k] = 1; // *
        }
        
        if (ops[k] == 0) {
            plus_count_prefix++;
        }
    }

    std::cout << "!";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << ops[i];
    }
    std::cout << std::endl;

    return 0;
}