#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    // Read and ignore coordinates
    for (int i = 0; i < N; ++i) {
        long long x, y;
        cin >> x >> y;
    }

    // Sieve for primes up to N-1
    vector<char> isPrime(N, true);
    if (N > 0) isPrime[0] = false;
    if (N > 1) isPrime[1] = false;
    for (int p = 2; (long long)p * p < N; ++p) {
        if (isPrime[p]) {
            for (int q = p * p; q < N; q += p) isPrime[q] = false;
        }
    }

    vector<int> P(N + 1);
    P[0] = 0;
    P[N] = 0;

    deque<int> outBuf;
    int reservedPrime = -1;
    bool blockHasTarget = false;

    int i = 1; // next city id to read

    auto read_advance = [&](bool blockHasTargetRef, int &reservedRef) -> bool {
        if (i > N - 1) return false;
        int id = i++;
        if (blockHasTargetRef && isPrime[id]) {
            if (reservedRef == -1) {
                reservedRef = id;
            } else {
                // Prefer the most recent prime for the target; push previous reserved to buffer
                outBuf.push_back(reservedRef);
                reservedRef = id;
            }
        } else {
            outBuf.push_back(id);
        }
        return true;
    };

    for (int pos = 1; pos <= N - 1; ++pos) {
        if ((pos - 1) % 10 == 0) {
            // Start of a new block
            reservedPrime = -1;
            blockHasTarget = (pos + 8 <= N - 1);
        }

        if (pos % 10 == 9) {
            // Target position: ensure we have a reserved prime
            while (reservedPrime == -1) {
                if (!read_advance(blockHasTarget, reservedPrime)) break;
            }
            if (reservedPrime != -1) {
                P[pos] = reservedPrime;
                reservedPrime = -1;
            } else {
                // Fallback (should be rare/unneeded): use from outBuf if available
                if (!outBuf.empty()) {
                    P[pos] = outBuf.front();
                    outBuf.pop_front();
                } else {
                    // Extremely unlikely fallback to avoid invalid output
                    P[pos] = 1;
                }
            }
            // After target is filled, no more target in this block
            blockHasTarget = false;
        } else {
            // Non-target position: emit next available from outBuf
            while (outBuf.empty()) {
                if (!read_advance(blockHasTarget, reservedPrime)) break;
            }
            if (!outBuf.empty()) {
                P[pos] = outBuf.front();
                outBuf.pop_front();
            } else {
                // If nothing left to read and outBuf empty, use reserved if any
                if (reservedPrime != -1) {
                    P[pos] = reservedPrime;
                    reservedPrime = -1;
                    blockHasTarget = false;
                } else {
                    // Extremely unlikely fallback to avoid invalid output
                    P[pos] = 1;
                }
            }
        }
    }

    cout << N + 1 << '\n';
    for (int k = 0; k <= N; ++k) {
        cout << P[k] << '\n';
    }
    return 0;
}