#include <bits/stdc++.h>

#ifdef LOCAL
#include <debug.h>
#else
#define debug(...)
#define debug_arr(...)
#define debug_endl(...)
#endif

std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

void solve() {
	for (int i = 1; i <= 100; i++) {
		std::ofstream fout(std::to_string(i) + ".in");
		fout << std::uniform_int_distribution<int>(1, 1000)(rng) << " " << std::uniform_int_distribution<int>(1, 1000)(rng) << " " << std::uniform_int_distribution<int>(1, 1000)(rng) << " " << std::uniform_int_distribution<int>(1, 1000)(rng) << "\n";
	}
}

int main() {
	std::ios::sync_with_stdio(false);
	std::cin.tie(nullptr);
	std::cout.setf(std::ios::fixed);
	std::cout.precision(10);

	solve();

	return 0;
}