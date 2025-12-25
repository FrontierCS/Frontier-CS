#include <iostream>
#include <vector>
#include <string>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::string s_found = "";
    int parity = 0;
    const int k = 50;
    const int m = 102;

    for (int i = 0; i < n; ++i) {
        int current_lane = i % k;
        int state_before = 2 * current_lane + parity;

        std::vector<int> a(m);
        std::vector<int> b(m);

        // Define transitions for the absorbing states. Once entered, stay there.
        a[100] = 100;
        b[100] = 100;
        a[101] = 101;
        b[101] = 101;

        // Define the standard transitions for the "lane and parity" machine.
        for (int lane = 0; lane < k; ++lane) {
            for (int p = 0; p < 2; ++p) {
                int current_state = 2 * lane + p;
                int next_lane = (lane + 1) % k;
                // On '0', preserve parity. On '1', flip parity.
                a[current_state] = 2 * next_lane + p;
                b[current_state] = 2 * next_lane + (1 - p);
            }
        }
        
        // Override the transition for the specific state we'll be in before S_i.
        // This directs the machine to an absorbing state based on S_i's value.
        a[state_before] = 100; // If S_i is '0'
        b[state_before] = 101; // If S_i is '1'

        // Make the query to the interactive judge.
        std::cout << "1 " << m;
        for (int val : a) {
            std::cout << " " << val;
        }
        for (int val : b) {
            std::cout << " " << val;
        }
        std::cout << std::endl;

        int result;
        std::cin >> result;

        // Deduce S_i from the result and update our known string and parity.
        if (result == 100) {
            s_found += '0';
        } else {
            s_found += '1';
            parity = 1 - parity;
        }
    }

    // After N queries, we have found the entire string.
    std::cout << "0 " << s_found << std::endl;

    return 0;
}