#include <iostream>

long long N;

// Function to ask a query and handle termination
int ask(long long x, long long y) {
    std::cout << x << " " << y << std::endl;
    int response;
    std::cin >> response;
    if (response == 0) {
        exit(0);
    }
    return response;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N;

    // Step 1: Find M = max(a, b)
    // M is the smallest value such that ask(M, M) must be 3 (or 0).
    long long l = 1, r = N;
    long long M = N + 1;
    while (l <= r) {
        long long mid = l + (r - l) / 2;
        if (mid == 0) { // Should not happen with l>=1
            l = 1;
            continue;
        }
        int response = ask(mid, mid);
        if (response == 3) {
            M = mid;
            r = mid - 1;
        } else { // response is 1 or 2
            l = mid + 1;
        }
    }

    // Step 2: Find a_cand assuming b = M
    // a_cand is the smallest value s.t. ask(a_cand, M) is not 1.
    l = 1, r = M;
    long long a_cand = M;
    while (l <= r) {
        long long mid = l + (r - l) / 2;
        if (mid == 0) {
            l = 1;
            continue;
        }
        int response = ask(mid, M);
        if (response != 1) { // can be 3
            a_cand = mid;
            r = mid - 1;
        } else { // response == 1
            l = mid + 1;
        }
    }

    // Step 3: Find b_cand assuming a = M
    // b_cand is the smallest value s.t. ask(M, b_cand) is not 2.
    l = 1, r = M;
    long long b_cand = M;
    while (l <= r) {
        long long mid = l + (r - l) / 2;
        if (mid == 0) {
            l = 1;
            continue;
        }
        int response = ask(M, mid);
        if (response != 2) { // can be 1 or 3
            b_cand = mid;
            r = mid - 1;
        } else { // response == 2
            l = mid + 1;
        }
    }

    // Step 4: Distinguish between (a_cand, M) and (M, b_cand)
    int final_resp = ask(a_cand, b_cand);
    if (final_resp == 1) { // a_cand < a, so a must be M
        ask(M, b_cand);
    } else { // final_resp == 2 (or 3, though unlikely), implies b_cand < b, so b must be M
        ask(a_cand, M);
    }
    
    return 0;
}