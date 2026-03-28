const styles = getComputedStyle(document.documentElement);

export const colors = {
    brightGreen: styles.getPropertyValue('--bright-green').trim(),
    orangeGold: styles.getPropertyValue('--orange-gold').trim(),
    alertRed: styles.getPropertyValue('--alert-red').trim(),
    lineChartBlue: styles.getPropertyValue('--chart-line-blue').trim(),
    gridColor: styles.getPropertyValue('--chart-grid').trim(),
    textMuted: styles.getPropertyValue('--text-muted').trim(),
    widgetBg: styles.getPropertyValue('--widget-bg').trim()
};