from matplotlib import pyplot as plt

Geb_b30 = [11, 10, 12, 14, 16, 19, 17, 14, 18, 17]
years_b30 = range(2008,2018)
Geb_a30 = [12, 10, 13, 14, 12, 13, 18, 16]
years_a30 = range(2010,2018)

fig, ax = plt.subplots()
ax.plot(years_b30, Geb_b30, label='Prices 2008-2018', color='blue')
ax.scatter(years_a30, Geb_a30, label='Prices 2010-2018', color = 'red')
legend = ax.legend(loc='center right', fontsize='x-large')
plt.xlabel('years')
plt.ylabel('prices')
plt.title('Comparison of the different prices')
plt.show()